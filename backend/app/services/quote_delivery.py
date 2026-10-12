from __future__ import annotations

import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from ipaddress import ip_address
from re import sub
from typing import Literal

import httpx
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.models.company import Company
from app.models.quote import Quote
from app.services.credentials import CredentialEncryptionError, decrypt_credential
from app.services.quote_pdf import generate_quote_pdf


class QuoteDeliveryConfigurationError(Exception):
    pass


class QuoteDeliveryProviderError(Exception):
    pass


@dataclass(frozen=True)
class SMTPConfiguration:
    host: str
    port: int
    username: str
    security: Literal["starttls", "ssl"]


def _connect_public_smtp(host: str, port: int, timeout: float) -> socket.socket:
    addresses = socket.getaddrinfo(
        host,
        port,
        type=socket.SOCK_STREAM,
    )
    public_addresses = []
    for address_info in addresses:
        family = address_info[0]
        address = address_info[4]
        if ip_address(address[0]).is_global:
            public_addresses.append((family, address))
    if not public_addresses:
        raise OSError("SMTP host must resolve to a public IP address.")

    last_error: OSError | None = None
    for family, address in public_addresses:
        connection = socket.socket(family, socket.SOCK_STREAM)
        try:
            connection.settimeout(timeout)
            connection.connect(address)
            return connection
        except OSError as exc:
            last_error = exc
            connection.close()
    if last_error is not None:
        raise last_error
    raise OSError("SMTP host has no usable public IP address.")


class PublicSMTP(smtplib.SMTP):
    def _get_socket(
        self,
        host: str,
        port: int,
        timeout: float,
    ) -> socket.socket:
        return _connect_public_smtp(host, port, timeout)


class PublicSMTP_SSL(smtplib.SMTP_SSL):
    def _get_socket(
        self,
        host: str,
        port: int,
        timeout: float,
    ) -> ssl.SSLSocket:
        connection = _connect_public_smtp(host, port, timeout)
        return self.context.wrap_socket(connection, server_hostname=host)


def _smtp_configuration(company: Company) -> SMTPConfiguration:
    host = company.smtp_host
    port = company.smtp_port
    username = company.smtp_username
    security = company.smtp_security
    if not host or port is None or not username:
        raise QuoteDeliveryConfigurationError(
            "Configure as credenciais SMTP da empresa em Configurações."
        )
    if security == "starttls":
        smtp_security: Literal["starttls", "ssl"] = "starttls"
    elif security == "ssl":
        smtp_security = "ssl"
    else:
        raise QuoteDeliveryConfigurationError(
            "O modo de segurança SMTP configurado não é suportado."
        )
    return SMTPConfiguration(host, port, username, smtp_security)


def _clean_header(value: str) -> str:
    return value.replace("\r", "").replace("\n", "").strip()


def _email_message(
    company: Company,
    quote: Quote,
    recipient: str,
    message: str | None,
    pdf_content: bytes,
) -> tuple[EmailMessage, str, SMTPConfiguration]:
    if not company.email or not company.smtp_password_encrypted:
        raise QuoteDeliveryConfigurationError(
            "Configure o email da empresa e as credenciais SMTP em Configurações."
        )
    smtp = _smtp_configuration(company)

    try:
        smtp_password = decrypt_credential(company.smtp_password_encrypted)
    except CredentialEncryptionError as exc:
        raise QuoteDeliveryConfigurationError(
            "As credenciais SMTP não podem ser descriptografadas. Revise a chave de criptografia."
        ) from exc

    email = EmailMessage()
    company_name = _clean_header(company.name)
    email["Subject"] = f"Orçamento {quote.number:04d} - {company_name}"
    email["From"] = formataddr(
        (company_name, _clean_header(company.email))
    )
    email["To"] = recipient
    email.set_content(
        message.strip()
        if message and message.strip()
        else (
            f"Olá,\n\nSegue em anexo o orçamento {quote.number:04d} "
            f"da empresa {company.name}.\n\nAtenciosamente,\n{company.name}"
        )
    )
    email.add_attachment(
        pdf_content,
        maintype="application",
        subtype="pdf",
        filename=f"orcamento-{quote.number:04d}.pdf",
    )
    return email, smtp_password, smtp


def _send_smtp_message(
    smtp: SMTPConfiguration,
    email: EmailMessage,
    password: str,
) -> None:
    context = ssl.create_default_context()
    try:
        if smtp.security == "ssl":
            with PublicSMTP_SSL(
                smtp.host,
                smtp.port,
                timeout=20,
                context=context,
            ) as server:
                server.login(smtp.username, password)
                server.send_message(email)
            return

        with PublicSMTP(smtp.host, smtp.port, timeout=20) as server:
            server.starttls(context=context)
            server.login(smtp.username, password)
            server.send_message(email)
    except (OSError, smtplib.SMTPException) as exc:
        raise QuoteDeliveryProviderError(
            "O servidor SMTP não concluiu o envio do orçamento."
        ) from exc


async def send_quote_email(
    quote: Quote,
    recipient: str | None,
    message: str | None,
) -> None:
    target_email = recipient or quote.client.email
    if not target_email:
        raise QuoteDeliveryConfigurationError(
            "Cadastre o email do cliente ou informe um destinatário."
        )
    pdf_content = await run_in_threadpool(generate_quote_pdf, quote)
    email, password, smtp = _email_message(
        quote.company, quote, target_email, message, pdf_content
    )

    await run_in_threadpool(_send_smtp_message, smtp, email, password)


def _normalize_phone(phone: str) -> str:
    if not phone.strip().startswith("+"):
        raise QuoteDeliveryConfigurationError(
            "Informe o telefone do cliente em formato internacional, começando com +."
        )
    digits = sub(r"\D", "", phone)
    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        raise QuoteDeliveryConfigurationError(
            "Informe o telefone do cliente com código do país, por exemplo +5511999999999."
        )
    return digits


async def send_quote_whatsapp(
    quote: Quote,
    recipient_phone: str | None,
    message: str | None,
) -> None:
    company = quote.company
    if not (company.phone and company.whatsapp_phone_number_id):
        raise QuoteDeliveryConfigurationError(
            "Configure o telefone de envio e o ID do número da Cloud API em Configurações."
        )
    if not company.whatsapp_access_token_encrypted:
        raise QuoteDeliveryConfigurationError(
            "Configure o token da WhatsApp Cloud API em Configurações."
        )
    target_phone = recipient_phone or quote.client.phone
    if not target_phone:
        raise QuoteDeliveryConfigurationError(
            "Cadastre o telefone do cliente ou informe um destinatário."
        )
    phone = _normalize_phone(target_phone)
    try:
        access_token = decrypt_credential(company.whatsapp_access_token_encrypted)
    except CredentialEncryptionError as exc:
        raise QuoteDeliveryConfigurationError(
            "As credenciais do WhatsApp não podem ser descriptografadas. Revise a chave de criptografia."
        ) from exc

    base_url = (
        f"https://graph.facebook.com/"
        f"{settings.whatsapp_graph_api_version}/"
        f"{company.whatsapp_phone_number_id}"
    )
    headers = {"Authorization": f"Bearer {access_token}"}
    pdf = await run_in_threadpool(generate_quote_pdf, quote)
    filename = f"orcamento-{quote.number:04d}.pdf"
    caption = (
        message.strip()
        if message and message.strip()
        else f"Olá! Segue o orçamento {quote.number:04d} da empresa {company.name}."
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            media_response = await client.post(
                f"{base_url}/media",
                headers=headers,
                data={
                    "messaging_product": "whatsapp",
                    "type": "application/pdf",
                },
                files={"file": (filename, pdf, "application/pdf")},
            )
            if not media_response.is_success:
                raise QuoteDeliveryProviderError(
                    "A WhatsApp Cloud API recusou o arquivo do orçamento "
                    f"(HTTP {media_response.status_code})."
                )
            try:
                media_id = media_response.json().get("id")
            except (ValueError, AttributeError) as exc:
                raise QuoteDeliveryProviderError(
                    "A WhatsApp Cloud API retornou uma resposta inválida ao receber o arquivo."
                ) from exc
            if not isinstance(media_id, str) or not media_id:
                raise QuoteDeliveryProviderError(
                    "A WhatsApp Cloud API não retornou o identificador do arquivo."
                )

            message_response = await client.post(
                f"{base_url}/messages",
                headers=headers,
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": phone,
                    "type": "document",
                    "document": {
                        "id": media_id,
                        "filename": filename,
                        "caption": caption,
                    },
                },
            )
            if not message_response.is_success:
                raise QuoteDeliveryProviderError(
                    "A WhatsApp Cloud API recusou o envio "
                    f"(HTTP {message_response.status_code})."
                )
    except httpx.TimeoutException as exc:
        raise QuoteDeliveryProviderError(
            "O envio pelo WhatsApp excedeu o tempo limite."
        ) from exc
    except httpx.RequestError as exc:
        raise QuoteDeliveryProviderError(
            "Não foi possível conectar à WhatsApp Cloud API."
        ) from exc
