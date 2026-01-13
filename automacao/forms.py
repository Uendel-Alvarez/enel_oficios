from django import forms
from .models import OficioEnel
from django.contrib.auth.models import User

class OficioEditForm(forms.ModelForm):
    # Forçamos o campo responsável a listar todos os usuários ativos
    responsavel = forms.ModelChoiceField(
        queryset=User.objects.all(),
        empty_label="Selecione um responsável",
        widget=forms.Select(attrs={'class': 'w-full bg-white border border-gray-300 rounded-lg p-2'})
    )
    class Meta:
        model = OficioEnel
        fields = ['numero_protocolo', 
            'orgao_solicitante', # Adicione este se não estiver
            'municipio', 
            'prazo', 
            'responsavel',
            'status_processamento']
        labels = {
            'status_processamento': 'Status do Ofício',
        }
        widgets = {
            'numero_protocolo': forms.TextInput(attrs={'class': 'form-input'}),
            'orgao_solicitante': forms.TextInput(attrs={'class': 'form-input'}),
            'municipio': forms.TextInput(attrs={'class': 'form-input'}),
            'prazo': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full bg-white border border-gray-300 rounded-lg p-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none'
            }),
            'responsavel': forms.Select(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded-lg p-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none appearance-none'
            }),
            'status_processamento': forms.Select(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded-lg p-2 text-gray-700 focus:ring-2 focus:ring-green-500 outline-none appearance-none'
            }),
        }


