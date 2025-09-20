from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from db.database import Base

class Servidor(Base):
    __tablename__ = "servidor"
    siape = Column(Integer, primary_key=True, index=True)
    campus = Column(String(50))
    servidor = Column(String(100))

class RAD(Base):
    __tablename__ = "rad"
    id = Column(Integer, primary_key=True, index=True)
    siape = Column(Integer, ForeignKey("servidor.siape"))
    periodo_letivo = Column(String(20))
    situacao = Column(String(20))
    aula = Column(Numeric(10,2))
    ensino = Column(Numeric(10,2))
    capacitacao = Column(Numeric(10,2))
    pesquisa = Column(Numeric(10,2))
    extensao = Column(Numeric(10,2))
    administracao_representacao = Column(Numeric(10,2))
    total = Column(Numeric(10,2))
    total_nao_homologado = Column(Numeric(10,2))
