FROM node:18
WORKDIR /app

# instala exatamente o que está no lockfile
COPY package.json package-lock.json ./
RUN npm ci --include=dev

# copia o restante do código
COPY . .

# CRA/Vite precisam ouvir fora do container
ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000
CMD ["npm","start"]
