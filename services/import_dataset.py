import os
import pandas as pd
from db.models import Servidor, RAD
from db.database import SessionLocal
from sqlalchemy.future import select


async def import_files_excel(folder: str):
    async with SessionLocal() as session:
        files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
        print(f"Arquivos encontrados: {files}")

        for file in files:
            caminho = os.path.join(folder, file)
            df = pd.read_excel(caminho)

            for _, row in df.iterrows():
                siape = int(row["Professor"].split("(")[-1].replace(")", ""))
                nome = row["Professor"].split("(")[0].strip()
                campus = row["Campus"]

                # 1. Inserir servidor se não existir
                result = await session.execute(
                    select(Servidor).where(Servidor.siape == siape)
                )
                servidor = result.scalar_one_or_none()

                if not servidor:
                    servidor = Servidor(siape=siape, servidor=nome, campus=campus)
                    session.add(servidor)
                    await session.flush()  # importante: garante que o servidor já esteja visível no banco para a FK

                # 2. Inserir RAD
                rad = RAD(
                    siape=siape,
                    periodo_letivo=row["Periodo letivo"],
                    situacao=row["Situação"],
                    aula=row["Aula"] or 0,
                    ensino=row["Ensino"] or 0,
                    capacitacao=row["Capacitação"] or 0,
                    pesquisa=row["Pesquisa"] or 0,
                    extensao=row["Extensão"] or 0,
                    administracao_representacao=row["Administração e Representação"] or 0,
                    total=row["Total"] or 0,
                    total_nao_homologado=row["Total não homologado"] or 0,
                )
                session.add(rad)

            await session.commit()
        print('Registros importados com sucesso!')
