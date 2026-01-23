from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import pandas as pd
import os

class OficioEnel(models.Model):
    data_recebimento = models.DateTimeField(auto_now_add=True)
    remetente = models.EmailField(max_length=255, null=True, blank=True)
    assunto = models.CharField(max_length=500, null=True, blank=True)
    corpo_email = models.TextField(null=True, blank=True)
    numero_protocolo = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=255, null=True, blank=True)
    quantidade_anexos = models.IntegerField(default=0)
    analise_ia = models.TextField(null=True, blank=True, verbose_name="Análise Detalhada da IA")
    
    # Este campo guardará o caminho do "arquivo principal" (geralmente o PDF do Ofício)
    caminho_arquivo = models.CharField(max_length=255, null=True, blank=True)
    
    STATUS_CHOICES = [
        (0, 'Pendente'),
        (1, 'Concluído'),
    ]
    status_processamento = models.IntegerField(choices=STATUS_CHOICES, default=0)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Responsável")
    prazo = models.DateField("Prazo Limite", null=True, blank=True)
    orgao_solicitante = models.CharField(max_length=255, null=True, blank=True)
    agrupamento_enel = models.CharField(max_length=50, null=True, blank=True)
    coordenadas_detectadas = models.CharField(max_length=255, null=True, blank=True)
    
    @property
    def esta_atrasado(self):
        if self.prazo and self.prazo < timezone.now().date() and self.status_processamento != 1:
            return True
        return False

    def __str__(self):
        return f"{self.numero_protocolo} - {self.municipio}"

# NOVA CLASSE: Permite que um Ofício tenha vários arquivos (PDF, Excel, Docx)
class AnexoOficio(models.Model):
    oficio = models.ForeignKey(OficioEnel, on_delete=models.CASCADE, related_name='anexos_arquivos')
    arquivo = models.FileField(upload_to='anexos/')
    nome_original = models.CharField(max_length=255)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_original

    @property
    def extensao(self):
        return os.path.splitext(self.arquivo.name)[1].lower()

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
    try:
        df = pd.read_excel(caminho_excel)
        df.columns = [str(c).strip() for c in df.columns]

        for _, row in df.iterrows():
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
    except Exception as e:
        print(f"Erro na importação de itens: {e}")