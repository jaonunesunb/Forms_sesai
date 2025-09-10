FROM node:18
WORKDIR /app

# Copia manifestos e instala deps com lock alinhado
COPY package.json package-lock.json ./
ENV PATH=/app/node_modules/.bin:$PATH
RUN npm ci

# Copia o restante do código
COPY . .

# CRA precisa ouvir fora do container
ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000
CMD ["npm", "start"]
