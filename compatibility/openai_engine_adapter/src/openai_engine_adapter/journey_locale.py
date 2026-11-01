"""Versioned presentation context; never identity, authorization or a memory key."""

import json
from typing import Literal

Locale = Literal["en-US", "pt-BR", "es-ES"]
LANGUAGES = {"en-US": "English", "pt-BR": "Brazilian Portuguese", "es-ES": "Spanish"}
PREFIX = "telecom-turn-v2\n"


def read_turn(message):
    if not isinstance(message, str) or not 1 <= len(message) <= 25000:
        raise ValueError("Invalid turn")
    if not message.startswith(PREFIX):
        if not message.strip() or len(message) > 4000:
            raise ValueError("Invalid legacy turn")
        return "en-US", message
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate turn field")
            result[key] = value
        return result
    data = json.loads(message[len(PREFIX):], object_pairs_hook=unique)
    if (not isinstance(data, dict) or set(data) != {"locale", "message"}
            or not isinstance(data["locale"], str) or data["locale"] not in LANGUAGES
            or not isinstance(data["message"], str)
            or not 1 <= len(data["message"].strip()) <= 4000
            or len(data["message"]) > 4000):
        raise ValueError("Invalid localized turn")
    # Never recursively parse the user message, even if it resembles an envelope.
    return data["locale"], data["message"]


TEXT = {
    "invoice.v1": (
        "Your synthetic invoice total is USD 79.90, due on 2026-12-01.",
        "O total da sua fatura sintética é USD 79,90, com vencimento em 01/12/2026.",
        "El total de tu factura sintética es USD 79,90, con vencimiento el 01/12/2026.",
    ),
    "connection.v1": (
        "The synthetic network reports no regional outage. Check the router power and cables, then compare a wired connection with Wi-Fi. If the problem persists, contact support.",
        "A rede sintética não indica indisponibilidade regional. Verifique a alimentação e os cabos do roteador e compare uma conexão por cabo com o Wi-Fi. Se o problema persistir, contate o suporte.",
        "La red sintética no indica una interrupción regional. Comprueba la alimentación y los cables del router y compara una conexión por cable con el Wi-Fi. Si el problema persiste, contacta con soporte.",
    ),
    "offer.v1": (
        "The synthetic {plan} plan offers {speed} Mbps for {price} per month. This demo account is eligible. No plan change has been requested.",
        "O plano sintético {plan} oferece {speed} Mbps por {price} por mês. Esta conta de demonstração é elegível. Nenhuma alteração de plano foi solicitada.",
        "El plan sintético {plan} ofrece {speed} Mbps por {price} al mes. Esta cuenta de demostración es elegible. No se ha solicitado ningún cambio de plan.",
    ),
    "proposal.v1": (
        "Simulate a change to {plan} ({speed} Mbps) at {price} per month? Approval produces a simulation receipt only; no live plan or charge changes.",
        "Simular uma mudança para {plan} ({speed} Mbps) por {price} por mês? A aprovação gera apenas um comprovante de simulação; nenhum plano real ou cobrança será alterado.",
        "¿Simular un cambio a {plan} ({speed} Mbps) por {price} al mes? La aprobación genera solo un comprobante de simulación; no se modifica ningún plan real ni cargo.",
    ),
    "simulation.v1": (
        "Simulation approved for {plan} at {price} per month. No live plan or charge was changed.",
        "Simulação aprovada para {plan} por {price} por mês. Nenhum plano real ou cobrança foi alterado.",
        "Simulación aprobada para {plan} por {price} al mes. No se modificó ningún plan real ni cargo.",
    ),
    "rejected.v1": (
        "The plan-change simulation was rejected. No plan or charge changed.",
        "A simulação de mudança de plano foi rejeitada. Nenhum plano ou cobrança foi alterado.",
        "La simulación de cambio de plan fue rechazada. No se modificó ningún plan ni cargo.",
    ),
    "expired.v1": (
        "The plan-change simulation was expired. No plan or charge changed.",
        "A simulação de mudança de plano expirou. Nenhum plano ou cobrança foi alterado.",
        "La simulación de cambio de plan caducó. No se modificó ningún plan ni cargo.",
    ),
    "clarification.v1": (
        "Please specify your invoice ID or whether you need connection help, a plan comparison, or a simulated change to fiber-500 or fiber-1000.",
        "Informe o identificador da fatura ou se precisa de ajuda com a conexão, comparação de planos ou simulação de mudança para fiber-500 ou fiber-1000.",
        "Indica el identificador de la factura o si necesitas ayuda con la conexión, comparar planes o simular un cambio a fiber-500 o fiber-1000.",
    ),
    "source_unavailable.v1": (
        "An approved procedure in the requested language is unavailable. The current source language is English. No translated operational steps are provided.",
        "Não há procedimento aprovado no idioma solicitado. O idioma atual da fonte é inglês. Nenhuma instrução operacional traduzida é fornecida.",
        "No hay un procedimiento aprobado en el idioma solicitado. El idioma actual de la fuente es inglés. No se proporcionan instrucciones operativas traducidas.",
    ),
}


def render(key, locale="en-US", **values):
    if locale not in LANGUAGES:
        raise ValueError("Unsupported locale")
    return TEXT[key][tuple(LANGUAGES).index(locale)].format(**values)


def price(amount, locale):
    if type(amount) is not int or amount < 0 or locale not in LANGUAGES:
        raise ValueError("Invalid money presentation")
    separator = "." if locale == "en-US" else ","
    return f"USD {amount // 100}{separator}{amount % 100:02d}"
