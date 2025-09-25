#!/bin/bash
# launch_cache_explorer.sh

# Diretório do projeto
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd "$PROJECT_DIR/templates"

# Função para verificar se a porta está disponível
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null; then
        return 1
    else
        return 0
    fi
}

# Função para abrir o navegador
open_browser() {
    local url=$1
    sleep 2  # Aguarda o servidor iniciar
    
    # Detecta o sistema operacional e abre o navegador apropriado
    case "$(uname -s)" in
        Darwin*)  # macOS
            open "$url"
            ;;
        Linux*)   # Linux
            if command -v xdg-open > /dev/null; then
                xdg-open "$url"
            elif command -v gnome-open > /dev/null; then
                gnome-open "$url"
            fi
            ;;
        CYGWIN*|MINGW*|MSYS*)  # Windows
            start "$url"
            ;;
    esac
}

# Porta padrão
PORT=8000

# Verifica se a porta padrão está em uso
while ! check_port $PORT; do
    echo "Porta $PORT em uso, tentando próxima..."
    PORT=$((PORT + 1))
done

# Inicia o servidor em segundo plano
echo "Iniciando Cache Explorer na porta $PORT..."
uvicorn metadata_web:app --port $PORT &
SERVER_PID=$!

# Abre o navegador
open_browser "http://localhost:$PORT"

# Captura CTRL+C para encerrar graciosamente
trap 'echo "Encerrando servidor..."; kill $SERVER_PID; exit 0' INT

# Aguarda o servidor
wait $SERVER_PID