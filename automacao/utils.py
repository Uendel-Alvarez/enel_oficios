import pandas as pd
from .models import ItemPlanilhaEnel

# [cite_start]Mapeamento baseado no seu documento sintetizado [cite: 1]
MAPEAMENTO_ESTRITUALIZADO = {
    'IDG': 'idg',
    'Endereço': 'endereco',
    'Bairro': 'bairro',
    'Município': 'municipio',
    'Tipo logradouro': 'tipo_logradouro',
    'Latitude': 'latitude', 
    'Longitude': 'longitude',
    'Tipo Lâmpada Anterior': 'tipo_lampada_anterior',
    'Potência Anterior': 'potencia_anterior',
    'Tempo da lâmpada ligadaAnterior': 'tempo_lampada_ligada_anterior',
    'Tipo Lâmpada Atual': 'tipo_lampada_atual',
    'Potência Atual': 'potencia_atual',
    'Tempo da lâmpada ligada Atual': 'tempo_lampada_ligada_atual',
    'Data Modificação': 'data_modificacao',
    'Informação se é Manutenção, Implantação ou Eficiência.': 'tipo_intervencao',
    'Tipo de medição': 'tipo_medicao',
    'Número do UC': 'numero_uc',
    'Tipo de Circuito': 'tipo_circuito',
    'Reator Situação (EXTERNO/INTERNO)Anterior': 'reator_situacao_anterior',
    'Reator Situação (EXTERNO/INTERNO)Atual': 'reator_situacao_atual',
    'Fabricante': 'fabricante',
    'Potência (W)': 'potencia_w',
    'Perda do Reator (W)Anterior': 'perda_reator_anterior',
    'Perda do Reator (W)Atual': 'perda_reator_atual',
    'Tipo de Rede': 'tipo_rede',
    'Número da Plaqueta': 'numero_plaqueta',
    'Código do poste': 'codigo_poste',
    'Documento: Nota fiscal, Nota de empenho, Ordem de serviço': 'doc_origem',
    'Ação (Substituição/Incremento/Retirada)': 'acao',
    'Fotografia com georreferencia (Anexo)': 'foto_geo',
    'Observação': 'observacao'
}

def importar_itens_seguro(caminho_excel, oficio_obj):
    df = pd.read_excel(caminho_excel)
    df.columns = [str(c).strip() for c in df.columns]

    for _, row in df.iterrows():
        # --- AJUSTE DE SEGURANÇA ---
        # Procura a coluna IDG de forma flexível
        coluna_idg = next((c for c in df.columns if 'IDG' in c.upper()), None)
        valor_idg = row.get(coluna_idg) if coluna_idg else None

        # Se não tiver IDG válido, pula essa linha (evita o erro NOT NULL)
        if pd.isna(valor_idg) or valor_idg == "":
            continue 
        
        dados = {'oficio_pai': oficio_obj}
        
        for nome_excel, campo_model in MAPEAMENTO_ESTRITUALIZADO.items():
            coluna_real = next((c for c in df.columns if nome_excel in c), None)
            
            if coluna_real:
                valor = row[coluna_real]
                
                if campo_model == 'data_modificacao' and pd.notnull(valor):
                    valor = pd.to_datetime(valor).date()
                
                if campo_model in ['idg', 'numero_uc', 'numero_plaqueta']:
                    try:
                        valor = int(float(valor)) if pd.notnull(valor) else 0
                    except:
                        valor = 0
                
                dados[campo_model] = valor
        
        ItemPlanilhaEnel.objects.create(**dados)
        