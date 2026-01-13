from django.db import models
from django.contrib.auth.models import User  # Certifique-se que é 'contrib'
from django.utils import timezone
import pandas as pd


class OficioEnel(models.Model):
    
    data_recebimento = models.DateTimeField(auto_now_add=True)
    remetente = models.EmailField(max_length=255, null=True, blank=True)
    assunto = models.CharField(max_length=500, null=True, blank=True)
    corpo_email = models.TextField(null=True, blank=True)
    numero_protocolo = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=255, null=True, blank=True)
    quantidade_anexos = models.IntegerField(default=0)
    caminho_arquivo = models.CharField(max_length=255, null=True, blank=True)
    STATUS_CHOICES = [
        (0, 'Pendente'),
        (1, 'Concluído'),
    ]
    status_processamento = models.IntegerField(choices=STATUS_CHOICES, default=0)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Responsável")
    prazo = models.DateField("Prazo Limite", null=True, blank=True)
    orgao_solicitante = models.CharField(max_length=255, null=True, blank=True)
   

     # Método para ajudar o template a mostrar se está atrasado (como na foto)
    @property
    def esta_atrasado(self):
        if self.prazo and self.prazo < timezone.now().date() and self.status_processamento != 2: # 2 = Concluído
            return True
        return False

    def __str__(self):
        return f"{self.numero_protocolo} - {self.municipio}"       




class ItemPlanilhaEnel(models.Model):
    oficio_pai = models.ForeignKey(OficioEnel, on_delete=models.CASCADE, related_name='itens')
    data_importacao = models.DateTimeField("Data de Importação", auto_now_add=True)
    # Obrigatórios 
    idg = models.IntegerField("IDG")
    endereco = models.TextField("Endereço")
    bairro = models.CharField("Bairro", max_length=255)
    municipio = models.CharField("Município", max_length=255)
    tipo_logradouro = models.CharField("Tipo logradouro", max_length=100)
    latitude = models.CharField("Latitude", max_length=50)
    longitude = models.CharField("Longitude", max_length=50)
    tipo_lampada_anterior = models.CharField("Tipo Lâmpada Anterior", max_length=100)
    potencia_anterior = models.CharField("Potência Anterior", max_length=50)
    tempo_lampada_ligada_anterior = models.CharField("Tempo lâmpada ligada Anterior", max_length=50)
    tipo_lampada_atual = models.CharField("Tipo Lâmpada Atual", max_length=100)
    potencia_atual = models.CharField("Potência Atual", max_length=50)
    tempo_lampada_ligada_atual = models.CharField("Tempo lâmpada ligada Atual", max_length=50)
    data_modificacao = models.DateField("Data Modificação")
    tipo_intervencao = models.CharField("Manutenção/Implantação/Eficiência", max_length=100)
    tipo_medicao = models.CharField("Tipo de medição", max_length=100)
    numero_uc = models.BigIntegerField("Número do UC")
    tipo_circuito = models.CharField("Tipo de Circuito", max_length=100)

    # Opcionais 
    reator_situacao_anterior = models.CharField(max_length=50, null=True, blank=True)
    reator_situacao_atual = models.CharField(max_length=50, null=True, blank=True)
    fabricante = models.CharField(max_length=255, null=True, blank=True)
    potencia_w = models.CharField(max_length=50, null=True, blank=True)
    perda_reator_anterior = models.CharField(max_length=50, null=True, blank=True)
    perda_reator_atual = models.CharField(max_length=50, null=True, blank=True)
    tipo_rede = models.CharField(max_length=100, null=True, blank=True)
    numero_plaqueta = models.BigIntegerField(null=True, blank=True)
    codigo_poste = models.CharField(max_length=100, null=True, blank=True)
    doc_origem = models.CharField(max_length=255, null=True, blank=True)
    acao = models.CharField(max_length=100, null=True, blank=True)
    foto_geo = models.CharField(max_length=255, null=True, blank=True)
    observacao = models.TextField(null=True, blank=True)


MAPEAMENTO_ESTRITUALIZADO = {
    'IDG': 'idg',
    'Endereço': 'endereco',
    'Bairro': 'bairro',
    'Município': 'municipio',
    'Tipo logradouro': 'tipo_logradouro',
    'Latitude': 'latitude', # Simplificado para evitar erro do texto longo 
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
    # Deixa as colunas do Excel limpas de espaços e em formato string
    df.columns = [str(c).strip() for c in df.columns]

    for _, row in df.iterrows():
        dados = {'oficio_pai': oficio_obj}
        
        for nome_excel, campo_model in MAPEAMENTO_ESTRITUALIZADO.items():
            # Tenta achar a coluna que CONTÉM o nome (ex: acha "Latitude..." por "Latitude")
            coluna_real = next((c for c in df.columns if nome_excel in c), None)
            
            if coluna_real:
                valor = row[coluna_real]
                
                # Tratamento de Data 
                if campo_model == 'data_modificacao' and pd.notnull(valor):
                    valor = pd.to_datetime(valor).date()
                
                # Tratamento de Números 
                if campo_model in ['idg', 'numero_uc', 'numero_plaqueta']:
                    valor = int(valor) if pd.notnull(valor) else 0
                
                dados[campo_model] = valor
        
        ItemPlanilhaEnel.objects.create(**dados)