# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Install build deps, Python packages, then remove build deps
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Copy root filesystem
COPY rootfs /

# Ensure run script is executable
RUN chmod a+x /etc/services.d/recorder-manager/run \
    && chmod a+x /etc/services.d/recorder-manager/finish

WORKDIR /usr/src/app

