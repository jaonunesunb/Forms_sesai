# Imagem leve e atual
FROM node:20-alpine

# 1) Diretório de trabalho
WORKDIR /app

# 2) Só os manifestos primeiro (melhora cache)
COPY package.json package-lock.json ./

# 3) Instalação determinística
RUN npm ci

# 4) Copia o restante do código
COPY . .

# 5) CRA precisa ouvir fora do container e hot reload no Docker/Windows
ENV HOST=0.0.0.0
ENV PORT=3000
ENV CHOKIDAR_USEPOLLING=true
ENV WATCHPACK_POLLING=true
# Se o HMR/WebSocket der erro, experimente:
# ENV WDS_SOCKET_PORT=0

EXPOSE 3000
# 6) Sobe o dev server
CMD ["npm", "start"]
