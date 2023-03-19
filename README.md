# Derzan E-commerce Scraper


Derzan is a web scraping tool for e-commerce websites. It is designed to scrape product details and prices from various e-commerce websites and stores them in a MongoDB database. It provides APIs to retrieve and export the scraped data.

## Supported Vendors


-   Makina
-   Vivense
-   Koctas


## Tech Stack

-   Python 3.9
-   FastAPI
-   Mongodb
-   Docker


## Deployment with docker


###  Installing docker using the repository

 [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

#### 1. Update the apt package index and install packages to allow apt to use a repository over HTTPS:

> sudo apt-get update\
> sudo apt-get install ca-certificates curl gnupg lsb-release

#### 2. Add Docker’s official GPG key:

> sudo mkdir -p /etc/apt/keyrings\
> curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

#### 3. Use the following command to set up the repository:
> echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

#### 4. Grant read permission for the Docker public key file before updating the package index:
> sudo chmod a+r /etc/apt/keyrings/docker.gpg\
> sudo apt-get update

#### 5. Install Docker Engine, containerd, and Docker Compose:
> sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-compose

## Building and running the application

###  Build the application image

> docker-compose build

###  Start and run the application container

> docker-compose up -d

###  **NOTE:** If you updated anything in the code or even access whitelist run:

> docker-compose up -d --force


## Other useful commands:

### List all images that are currently stored

> docker images

### List all running containers

> docker ps

### All in one command

> git pull && docker-compose up -d --build --force-recreate && docker compose logs -f


