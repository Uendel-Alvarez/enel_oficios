from django.contrib import admin
from .models import OficioEnel, ItemPlanilhaEnel

# Permite visualizar os itens da planilha dentro da página do Ofício Pai
class ItemPlanilhaInline(admin.TabularInline):
    model = ItemPlanilhaEnel
    extra = 0
    readonly_fields = ('data_importacao',)
    # Exibir apenas colunas principais no resumo para não travar a tela
    fields = ('idg', 'municipio', 'bairro', 'data_modificacao', 'tipo_intervencao')

@admin.register(OficioEnel)
class OficioEnelAdmin(admin.ModelAdmin):
    list_display = ('numero_protocolo', 'municipio', 'responsavel', 'prazo','data_recebimento', 'status_processamento', 'quantidade_anexos')
    list_filter = ('responsavel', 'municipio', 'status_processamento', 'data_recebimento')
    search_fields = ('numero_protocolo', 'municipio', 'assunto')
    fields = ('assunto', 'remetente', 'data_recebimento', 'municipio', 'numero_protocolo', 'responsavel', 'prazo', 'status_processamento', 'corpo_email')
    inlines = [ItemPlanilhaInline]

@admin.register(ItemPlanilhaEnel)
class ItemPlanilhaEnelAdmin(admin.ModelAdmin):
    list_display = ('idg', 'municipio', 'bairro', 'data_modificacao', 'tipo_intervencao', 'oficio_pai')
    list_filter = ('municipio', 'tipo_intervencao', 'data_modificacao')
    search_fields = ('idg', 'municipio', 'endereco')

    # ESTA LINHA ABAIXO É UMA CORREÇÃO:
    # Ela avisa ao Django que esse campo não pode ser editado na mão, apenas visualizado.
    readonly_fields = ('data_importacao',)

    # ORGANIZAÇÃO DOS 31 CAMPOS EM BLOCOS (Fieldsets)
    fieldsets = (
        ('Identificação do Item', {
            'fields': ('oficio_pai', 'idg', 'data_importacao')
        }),
        ('Localização', {
            'fields': ('municipio', 'bairro', 'endereco', 'tipo_logradouro', ('latitude', 'longitude'))
        }),
        ('Especificações da Lâmpada', {
            'fields': (
                ('tipo_lampada_anterior', 'potencia_anterior', 'tempo_lampada_ligada_anterior'),
                ('tipo_lampada_atual', 'potencia_atual', 'tempo_lampada_ligada_atual'),
            )
        }),
        ('Dados da Instalação', {
            'fields': ('data_modificacao', 'tipo_intervencao', 'tipo_medicao', 'numero_uc', 'tipo_circuito')
        }),
        ('Campos Opcionais (Reator e Rede)', {
            'classes': ('collapse',), # Este bloco começa escondido
            'fields': (
                ('reator_situacao_anterior', 'reator_situacao_atual'),
                ('perda_reator_anterior', 'perda_reator_atual'),
                'fabricante', 'potencia_w', 'tipo_rede', 'numero_plaqueta', 'codigo_poste'
            )
        }),
        ('Documentação e Observações', {
            'fields': ('doc_origem', 'acao', 'foto_geo', 'observacao')
        }),
    )