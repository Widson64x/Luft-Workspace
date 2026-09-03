# Arquivo: Luft-Control/Models/SqlServer/Permissoes.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from App.Models.SqlServer.Usuario import Base

class Tb_Sistema(Base):
    __tablename__ = "Tb_Sistema"
    __table_args__ = {"schema": "intec.dbo"}

    Id_Sistema = Column(Integer, primary_key=True, autoincrement=True)
    Nome_Sistema = Column(String(100), unique=True, nullable=False)
    Descricao_Sistema = Column(String(255))
    Ativo = Column(Boolean, default=True)

class Tb_Permissao(Base):
    __tablename__ = "Tb_Permissao"
    __table_args__ = {"schema": "intec.dbo"}

    Id_Permissao = Column(Integer, primary_key=True, autoincrement=True)
    Id_Sistema = Column(Integer, ForeignKey("intec.dbo.Tb_Sistema.Id_Sistema"), nullable=False)
    Chave_Permissao = Column(String(100), nullable=False)
    Descricao_Permissao = Column(String(255))
    Categoria_Permissao = Column(String(50))

class Tb_PermissaoGrupo(Base):
    __tablename__ = "Tb_PermissaoGrupo"
    __table_args__ = {"schema": "intec.dbo"}

    Id_Vinculo = Column(Integer, primary_key=True, autoincrement=True)
    
    # REMOVIDO o ForeignKey para evitar o erro de Cross-Database com o LuftInforma
    Codigo_UsuarioGrupo = Column(Integer, nullable=False) 
    
    Id_Permissao = Column(Integer, ForeignKey("intec.dbo.Tb_Permissao.Id_Permissao"))

class Tb_PermissaoUsuario(Base):
    __tablename__ = "Tb_PermissaoUsuario"
    __table_args__ = {"schema": "intec.dbo"}

    Id_Vinculo = Column(Integer, primary_key=True, autoincrement=True)
    
    # REMOVIDO o ForeignKey para evitar o erro de Cross-Database com o LuftInforma
    Codigo_Usuario = Column(Integer, nullable=False) 
    
    Id_Permissao = Column(Integer, ForeignKey("intec.dbo.Tb_Permissao.Id_Permissao"))
    Conceder = Column(Boolean, default=True)

class Tb_LogAcesso(Base):
    __tablename__ = "Tb_LogAcesso"
    __table_args__ = {"schema": "intec.dbo"}

    Id_Log = Column(Integer, primary_key=True, autoincrement=True)
    Id_Sistema = Column(Integer, ForeignKey("intec.dbo.Tb_Sistema.Id_Sistema"), nullable=True)
    Id_Usuario = Column(Integer, nullable=True)
    Nome_Usuario = Column(String(150))
    Rota_Acessada = Column(String(200))
    Metodo_Http = Column(String(10))
    Ip_Origem = Column(String(50))
    Permissao_Exigida = Column(String(100))
    Acesso_Permitido = Column(Boolean)
    Data_Hora = Column(DateTime, default=datetime.now)

    # NOVAS COLUNAS:
    Parametros_Requisicao = Column(Text, nullable=True) # Vai armazenar o que o usuário enviou
    Resposta_Acao = Column(Text, nullable=True)


class Tb_LogDetalhe(Base):
    """Detalhe granular das operacoes auditadas pelo LuftCore."""

    __tablename__ = "Tb_LogDetalhe"
    __table_args__ = {"schema": "intec.dbo"}

    Id_LogDetalhe = Column(Integer, primary_key=True, autoincrement=True)
    Id_Sistema = Column(Integer, ForeignKey("intec.dbo.Tb_Sistema.Id_Sistema"), nullable=True)
    Id_LogAcesso = Column(Integer, ForeignKey("intec.dbo.Tb_LogAcesso.Id_Log"), nullable=True)
    Id_Usuario = Column(Integer, nullable=True)
    Nome_Usuario = Column(String(150), nullable=True)
    Acao = Column(String(100), nullable=False)
    Recurso = Column(String(100), nullable=False)
    Id_Recurso = Column(String(100), nullable=True)
    Descricao = Column(Text, nullable=True)
    Dados_Anteriores_Json = Column(Text, nullable=True)
    Dados_Novos_Json = Column(Text, nullable=True)
    Ip_Origem = Column(String(50), nullable=True)
    User_Agent = Column(String(500), nullable=True)
    Data_Hora = Column(DateTime, default=datetime.now, nullable=False)
    Severidade = Column(String(20), default="BAIXA", nullable=False)
    Traceback = Column(Text, nullable=True)
