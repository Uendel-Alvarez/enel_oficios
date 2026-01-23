import os
import csv
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.utils.timezone import now
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required

# Imports do seu projeto
from .models import OficioEnel, importar_itens_seguro
from .forms import OficioEditForm
from .utils_ia import extrair_dados_oficio

@login_required
def exportar_oficios_csv(request):
    termo_busca = request.GET.get('buscar')
    filtro_status = request.GET.get('status')
    oficios = OficioEnel.objects.all()

    if termo_busca:
        oficios = oficios.filter(
            Q(numero_protocolo__icontains=termo_busca) | 
            Q(municipio__icontains=termo_busca)
        )
    if filtro_status and filtro_status != "Todos":
        oficios = oficios.filter(status_processamento=filtro_status)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="relatorio_oficios.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Protocolo', 'Municipio', 'Data Recebimento', 'Prazo', 'Status'])

    for oficio in oficios:
        status_texto = "Concluído" if oficio.status_processamento == 1 else "Pendente"
        writer.writerow([
            oficio.numero_protocolo,
            oficio.municipio,
            oficio.data_recebimento,
            oficio.prazo if oficio.prazo else 'N/A',
            status_texto
        ])
    return response

@login_required
def listagem_oficios(request):
    oficios = OficioEnel.objects.all().order_by('-data_recebimento')
    termo_busca = request.GET.get('buscar')
    filtro_status = request.GET.get('status')

    if termo_busca:
        oficios = oficios.filter(
            Q(numero_protocolo__icontains=termo_busca) | 
            Q(municipio__icontains=termo_busca)
        )

    if filtro_status and filtro_status != "Todos":
        oficios = oficios.filter(status_processamento=filtro_status)

    context = {
        'oficios': oficios,
        'total_oficios': OficioEnel.objects.count(),
        'pendentes': OficioEnel.objects.filter(status_processamento=0).count(),
        'atrasados': sum(1 for o in OficioEnel.objects.all() if o.esta_atrasado),
        'termo_busca': termo_busca,
    }
    return render(request, 'oficios_list.html', context)

@login_required
def monitoramento_view(request):
    oficios = OficioEnel.objects.all().order_by('-data_recebimento')
    busca_geral = request.GET.get('busca_geral')
    if busca_geral:
        oficios = oficios.filter(
            Q(remetente__icontains=busca_geral) | 
            Q(assunto__icontains=busca_geral)
        )

    protocolo = request.GET.get('protocolo')
    if protocolo:
        oficios = oficios.filter(numero_protocolo__icontains=protocolo)

    return render(request, 'monitoramento.html', {'oficios': oficios})

@login_required
def home_view(request):
    return render(request, 'home.html')

@login_required
def listagem_pendentes(request):
    oficios_pendentes = OficioEnel.objects.filter(
        Q(status_processamento=0) | Q(responsavel__isnull=True) | Q(prazo__isnull=True)
    ).order_by('-data_recebimento')

    return render(request, 'oficios_pendentes.html', {
        'oficios': oficios_pendentes,
        'titulo_pagina': 'Ofícios Pendentes de Dados'
    })

@login_required
def upload_manual(request):
    if request.method == 'POST':
        arquivos = request.FILES.getlist('arquivo')
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'anexos')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        fs = FileSystemStorage(location=upload_dir)
        
        for f in arquivos:
            # 1. Salva o arquivo fisicamente
            nome_salvo = fs.save(f.name, f)
            caminho_completo = fs.path(nome_salvo)

            # 2. IA processa o arquivo
            dados_ia = extrair_dados_oficio(caminho_completo)
            
            if dados_ia is None:
                messages.warning(request, f"A IA não conseguiu ler os dados de {f.name}.")
                dados_ia = {}

            # 3. Organiza o resumo da IA para o campo analise_ia
            resumo_ia = (
                f"DATA DO DOC: {dados_ia.get('data', 'Não identificada')}\n"
                f"ÓRGÃO: {dados_ia.get('orgao_solicitante', 'Não identificado')}\n\n"
                f"RESUMO DOS PEDIDOS:\n{dados_ia.get('pedidos_servicos', 'Nenhum detalhe extraído.')}"
            )

            # 4. Define o caminho relativo para o banco
            caminho_relativo_db = os.path.join('anexos', nome_salvo)

            # 5. Criação do registro (Agora com analise_ia existindo no banco)
            novo_oficio = OficioEnel.objects.create(
                numero_protocolo=dados_ia.get("numero_protocolo", "NÃO ENCONTRADO"),
                municipio=dados_ia.get("municipio", "NÃO ENCONTRADO"),
                orgao_solicitante=dados_ia.get("orgao_solicitante", "NÃO ENCONTRADO"),
                assunto=dados_ia.get("assunto", f"Upload Manual: {f.name}"),
                analise_ia=resumo_ia, 
                data_recebimento=now(),
                remetente=request.user.username,
                caminho_arquivo=caminho_relativo_db,
                status_processamento=0
            )

            # Lógica para Excel (Mantendo o seu try/except de segurança)
            if f.name.lower().endswith(('.xlsx', '.xls')):
                try:
                    importar_itens_seguro(caminho_completo, novo_oficio)
                    messages.success(request, f"Planilha {f.name} importada e vinculada!")
                except Exception as e:
                    messages.error(request, f"Erro ao processar dados da planilha: {e}")
            else:
                messages.success(request, f"Ofício {novo_oficio.numero_protocolo} registrado!")
            
        return redirect('listagem_pendentes')
    
    return render(request, 'upload_manual.html')
@login_required
def editar_oficio(request, pk):
    oficio = get_object_or_404(OficioEnel, pk=pk)
    
    if request.method == 'POST':
        form = OficioEditForm(request.POST, instance=oficio)
        if form.is_valid():
            instancia = form.save(commit=False)
            if instancia.prazo and instancia.responsavel:
                instancia.status_processamento = 1
                messages.success(request, f"Ofício {instancia.numero_protocolo} CONCLUÍDO!")
            else:
                instancia.status_processamento = 0
                messages.info(request, "Alterações salvas. Ofício continua Pendente.")

            instancia.save()
            form.save_m2m()
            return redirect('listagem_pendentes')
        else:
            messages.error(request, "Erro ao validar os dados.")
    else:
        form = OficioEditForm(instance=oficio)
    
    return render(request, 'editar_oficio.html', {'form': form, 'oficio': oficio})

@login_required
def oficio_detalhe_fragmento(request, oficio_id):
    oficio = get_object_or_404(OficioEnel, id=oficio_id)
    return render(request, 'oficio_detalhe_fragmento.html', {'oficio': oficio})
