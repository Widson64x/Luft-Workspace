"""Rotas de testes e desenvolvimento para envio de notificacoes."""

from flask import current_app
from flask_login import login_required
from App.Routes.Principal import PrincipalBp

USUARIO = 2280
GRUPO = 6

# --- ROTAS PARA TESTE DE MECÂNICAS DE NOTIFICAÇÃO ---

@PrincipalBp.route("/api/teste-notificacao/usuario", methods=["GET"])
@login_required
def ApiTesteNotificacaoUsuario():
    notif = current_app.extensions.get("luft_notificacoes")
    if notif:
        try:
            notif.criar_notificacao(
                titulo="Notificação Direcionada",
                mensagem="Olá Usuário, esta notificação foi disparada especificamente para você!",
                tipo="SUCESSO",
                categoria="USUARIO",
                id_usuario_destino=USUARIO
            )
            return {"status": "ok", "mensagem": "Enviada para o usuário logado!"}
        except Exception as e:
            current_app.logger.exception("Erro na API Teste Notificacao Usuario")
            return {"status": "erro", "mensagem": str(e)}, 500
    return {"status": "erro"}, 500


@PrincipalBp.route("/api/teste-notificacao/grupo", methods=["GET"])
@login_required
def ApiTesteNotificacaoGrupo():
    notif = current_app.extensions.get("luft_notificacoes")
    if notif:
        try:
            notif.criar_notificacao(
                titulo="Notificação para seu Grupo",
                mensagem="Todos os membros com o seu mesmo nível de acesso e cargo devem estar recebendo isso.",
                tipo="INFO",
                categoria="GERAL",
                id_grupo_destino=GRUPO
            )
            return {"status": "ok", "mensagem": "Enviada para o grupo!"}
        except Exception as e:
            current_app.logger.exception("Erro na API Teste Notificacao Grupo")
            return {"status": "erro", "mensagem": str(e)}, 500
    return {"status": "erro"}, 500


@PrincipalBp.route("/api/teste-notificacao/comunicado", methods=["GET"])
@login_required
def ApiTesteNotificacaoContexto():
    notif = current_app.extensions.get("luft_notificacoes")
    if notif:
        try:
            notif.criar_notificacao(
                titulo="Novo Comunicado Interno!",
                mensagem="A diretoria publicou um novo comunicado sobre as políticas de fim de ano.",
                tipo="INFO",
                categoria="GERAL",
                metadados={
                    "acao_url": "/configuracoes",
                    "texto_link": "Ler Comunicado na Íntegra"
                }
            )
            return {"status": "ok", "mensagem": "Enviada com link!"}
        except Exception as e:
            current_app.logger.exception("Erro na API Teste Notificacao Contexto")
            return {"status": "erro", "mensagem": str(e)}, 500
    return {"status": "erro"}, 500


@PrincipalBp.route("/api/teste-notificacao/agendada", methods=["GET"])
@login_required
def ApiTesteNotificacaoAgendada():
    notif = current_app.extensions.get("luft_notificacoes")
    if notif:
        try:
            from datetime import datetime, timedelta
            exibir_em = datetime.now() + timedelta(seconds=15)
            notif.criar_notificacao(
                titulo="Você viajou no tempo! 🕒",
                mensagem="Essa notificação foi criada há 15 segundos, mas só foi programada para aparecer pra você agora.",
                tipo="INFO",
                categoria="GERAL",
                exibir_a_partir_de=exibir_em
            )
            return {"status": "ok", "mensagem": "Agendada para 15s no futuro!"}
        except Exception as e:
            current_app.logger.exception("Erro na API Teste Notificacao Agendada")
            return {"status": "erro", "mensagem": str(e)}, 500
    return {"status": "erro"}, 500
