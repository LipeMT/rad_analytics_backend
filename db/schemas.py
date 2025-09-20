from pydantic import BaseModel
from typing import Optional

class ServidorSchema(BaseModel):
    siape: int
    campus: str
    servidor: str

class RADSchema(BaseModel):
    siape: int
    periodo_letivo: str
    situacao: str
    aula: float
    ensino: float
    capacitacao: float
    pesquisa: float
    extensao: float
    administracao_representacao: float
    total: float
    total_nao_homologado: float
