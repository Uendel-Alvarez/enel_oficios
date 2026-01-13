from django.shortcuts import render
from .models import OficioEnel
from django.db.models import Q # Importante para buscas complexas
from django.db.models import Count
from datetime import date
import csv
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .forms import OficioEditForm
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .management.commands.process_emails import Command as EmailProcessor
from automacao.management.commands.process_emails import processar_arquivo_individual
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import OficioEnel
from django.contrib import messages
from .forms import OficioEditForm # Certifique-se de que o import está correto


@login_required
def exportar_oficios_csv(request):
    # 1. Captura os mesmos filtros da tela de listagem
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

    # 2. Configura a resposta do navegador para baixar um arquivo CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="relatorio_oficios.csv"'

    # 3. Cria o escritor CSV e define o cabeçalho
    writer = csv.writer(response, delimiter=';') # Usamos ponto e vírgula para abrir direto no Excel PT-BR
    writer.writerow(['Protocolo', 'Municipio', 'Data Recebimento', 'Prazo', 'Status'])

    # 4. Escreve os dados
    for oficio in oficios:
        # Lógica manual de status caso o método automático falhe
        status_texto = "Concluído" if oficio.status_processamento == 1 else "Pendente"

        writer.writerow([
            oficio.numero_protocolo,
            oficio.municipio,
            oficio.data_recebimento,
            oficio.prazo if oficio.prazo else 'N/A',
            status_texto  # Usamos a variável que criamos acima
        ])
    return response

@login_required
def listagem_oficios(request):
    # 1. Pega todos os ofícios inicialmente
    oficios = OficioEnel.objects.all().order_by('-data_recebimento')

    # 2. Captura os termos de busca do formulário (via GET)
    termo_busca = request.GET.get('buscar')
    filtro_status = request.GET.get('status')

    # 3. Aplica o filtro de texto (Protocolo ou Município/Órgão)
    if termo_busca:
        oficios = oficios.filter(
            Q(numero_protocolo__icontains=termo_busca) | 
            Q(municipio__icontains=termo_busca)
        )

    # 4. Aplica o filtro de Status
    if filtro_status and filtro_status != "Todos":
        oficios = oficios.filter(status_processamento=filtro_status)

    # 5. Cálculos para os Cards Superiores (refletindo os filtros)
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
    # Pega todos os ofícios salvos no banco, ordenados pelo mais recente
    oficios = OficioEnel.objects.all().order_by('-data_recebimento')
    
    # Filtro por Remetente ou Assunto (Barra central)
    busca_geral = request.GET.get('busca_geral')
    if busca_geral:
        oficios = oficios.filter(
            Q(remetente__icontains=busca_geral) | 
            Q(assunto__icontains=busca_geral)
        )

    # Filtro por Protocolo (Barra superior)
    protocolo = request.GET.get('protocolo')
    if protocolo:
        oficios = oficios.filter(numero_protocolo__icontains=protocolo)


    return render(request, 'monitoramento.html', {'oficios': oficios})

@login_required
def home_view(request):
    return render(request, 'home.html')


@login_required
def listagem_pendentes(request):
    # Filtra apenas status 0 (Pendente) ou onde não há responsável/prazo
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
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'anexos'))
        
        for f in arquivos:
            # 1. Cria o registro no banco antes de processar
            novo_oficio = OficioEnel.objects.create(
                assunto=f"Upload Manual: {f.name}",
                data_recebimento=now(),
                remetente=request.user.username,
                corpo_email="Arquivo carregado manualmente pelo usuário.",
                status_processamento=0
            )

            # 2. Salva o arquivo no disco
            nome_salvo = fs.save(f.name, f)
            caminho_completo = fs.path(nome_salvo)

            # 3. CHAMA A MESMA INTELIGÊNCIA DO E-MAIL!
            processar_arquivo_individual(caminho_completo, novo_oficio)
            
        return redirect('listagem_pendentes')
    
    return render(request, 'upload_manual.html')



@login_required
def editar_oficio(request, pk):
    # 1. Busca o objeto ou retorna 404
    oficio = get_object_or_404(OficioEnel, pk=pk)
    
    if request.method == 'POST':
        # 2. Preenche o formulário com os dados vindos do navegador
        form = OficioEditForm(request.POST, instance=oficio)
        
        if form.is_valid():
            # 3. Salva os dados básicos (Município, Protocolo, etc.)
            instancia = form.save(commit=False)
            
            # 4. LÓGICA INTELIGENTE: Se preencheu Prazo E Responsável, vira Concluído (1)
            # Caso contrário, permanece como Pendente (0)
            if instancia.prazo and instancia.responsavel:
                instancia.status_processamento = 1
                messages.success(request, f"Ofício {instancia.numero_protocolo} CONCLUÍDO e atualizado!")
            else:
                instancia.status_processamento = 0
                messages.info(request, "Alterações salvas. Ofício continua como Pendente.")

            instancia.save()
            form.save_m2m() # Importante para campos ManyToMany, se houver
            
            # 5. Redireciona para a lista de pendentes
            return redirect('listagem_pendentes')
        else:
            # Em caso de erro no formulário
            print(form.errors)
            messages.error(request, "Erro ao validar os dados. Verifique os campos.")
    else:
        # 6. Método GET: Apenas exibe o formulário preenchido com os dados atuais
        form = OficioEditForm(instance=oficio)
    
    # IMPORTANTE: Corrigido o caminho para 'automacao/editar_oficio.html'
    return render(request, 'editar_oficio.html', {
        'form': form, 
        'oficio': oficio
    })


