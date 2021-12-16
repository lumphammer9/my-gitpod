FROM gitpod/workspace-full
RUN apt-get update && sudo apt-get install -y gnupg software-properties-common curl
USER gitpod
