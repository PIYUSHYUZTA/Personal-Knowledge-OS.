FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build application
RUN npm run build

# Expose port
EXPOSE 5173

# Run development server (can be changed to preview for production)
CMD ["npm", "run", "dev"]
