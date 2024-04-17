FROM python:3.9-slim-buster

#Install SQL Server (to run queries with pyodbc)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    libgssapi-krb5-2

# Instalar dependências e o driver ODBC do SQL Server
RUN apt-get update \
    && apt-get install -y unixodbc unixodbc-dev odbcinst odbcinst1debian2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download and install the Microsoft ODBC driver for SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17

# To this pyodbc SQL server setup, use 'DRIVER={ODBC Driver 17 for SQL Server}' in the connection string

WORKDIR /app

COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expõe a porta do aplicativo
EXPOSE 8080 5000 80 443

COPY . .

CMD [ "python", "app.py", "-m" , "flask", "run", "--host=0.0.0.0"]