#!/bin/bash

# Script para instalar todos os módulos Poetry automaticamente
# Descobre módulos dinamicamente pelos diretórios que contêm pyproject.toml

set -e  # Parar em caso de erro

echo "🚀 Iniciando instalação de todos os módulos..."
echo

# Descobrir módulos automaticamente
modules=()
for dir in */; do
    if [[ -f "${dir}pyproject.toml" ]]; then
        module_name=$(basename "$dir")
        modules+=("$module_name")
    fi
done

if [[ ${#modules[@]} -eq 0 ]]; then
    echo "❌ Nenhum módulo encontrado (nenhum diretório com pyproject.toml)"
    exit 1
fi

echo "📦 Módulos encontrados: ${modules[*]}"
echo

# Instalar cada módulo
for module in "${modules[@]}"; do
    echo "🔧 Instalando módulo: $module"
    echo "   Diretório: $module/"
    
    cd "$module"
    
    # Verificar se pyproject.toml existe
    if [[ ! -f "pyproject.toml" ]]; then
        echo "   ⚠️  pyproject.toml não encontrado, pulando..."
        cd ..
        continue
    fi
    
    # Executar poetry install
    if poetry install; then
        echo "   ✅ $module instalado com sucesso"
    else
        echo "   ❌ Erro ao instalar $module"
        cd ..
        exit 1
    fi
    
    cd ..
    echo
done

echo "🎉 Instalação concluída para todos os módulos!"
echo "📋 Módulos instalados: ${modules[*]}"