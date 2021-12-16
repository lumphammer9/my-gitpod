FROM gitpod/workspace-full
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
         gnupg \
         software-properties-common \
         curl
USER gitpod
