# OpenTOPAS on Ubuntu 20.04 (focal) desktop with browser-accessible VNC
# Uses dorowu/ubuntu-desktop-lxde-vnc:focal (latest available tag)
# Qt6 is installed via aqtinstall since focal ships only Qt5
FROM dorowu/ubuntu-desktop-lxde-vnc:focal

ENV DEBIAN_FRONTEND=noninteractive
ENV QT6_DIR=/opt/Qt/6.5.3/gcc_64

# ── Step 1-4: System dependencies ────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    libexpat1-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libxt-dev \
    xorg-dev \
    build-essential \
    libharfbuzz-dev \
    cmake \
    git \
    wget \
    python3-pip \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libfreetype6 \
    libx11-xcb1 \
    libxcb-glx0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Qt 6.5.3 via aqtinstall (Ubuntu 20.04 focal ships only Qt5)
RUN pip3 install aqtinstall \
    && aqt install-qt linux desktop 6.5.3 -O /opt/Qt \
    && pip3 uninstall -y aqtinstall

# ── Step 5: Download and extract Geant4 source ───────────────────────────────
RUN mkdir -p /root/Applications/GEANT4 \
    && cd /root/Applications/GEANT4 \
    && wget -q https://gitlab.cern.ch/geant4/geant4/-/archive/v11.3.2/geant4-v11.3.2.tar.gz \
    && tar -zxf geant4-v11.3.2.tar.gz \
    && rm geant4-v11.3.2.tar.gz

# ── Step 6: Download and extract Geant4 data files ───────────────────────────
RUN mkdir -p /root/Applications/GEANT4/G4DATA \
    && cd /root/Applications/GEANT4/G4DATA \
    && wget -q https://cern.ch/geant4-data/datasets/G4NDL.4.7.1.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4EMLOW.8.6.1.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4PhotonEvaporation.6.1.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4RadioactiveDecay.6.1.2.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4PARTICLEXS.4.1.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4ABLA.3.3.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4INCL.1.2.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4ENSDFSTATE.3.0.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4CHANNELING.1.0.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4NUDEXLIB.1.0.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4URRPT.1.1.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4PII.1.3.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4RealSurface.2.2.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4SAIDDATA.2.0.tar.gz \
    && wget -q https://cern.ch/geant4-data/datasets/G4TENDL.1.4.tar.gz \
    && for f in *.tar.gz; do tar -zxf "$f" && rm "$f"; done

# ── Step 7: Build and install Geant4 ─────────────────────────────────────────
RUN cd /root/Applications/GEANT4 \
    && mkdir geant4-build geant4-install \
    && cd geant4-build \
    && cmake ../geant4-v11.3.2 \
        -DGEANT4_INSTALL_DATA=OFF \
        -DGEANT4_BUILD_MULTITHREADED=ON \
        -DGEANT4_BUILD_VERBOSE_CODE=OFF \
        -DCMAKE_INSTALL_PREFIX=../geant4-install \
        -DCMAKE_PREFIX_PATH=/opt/Qt/6.5.3/gcc_64 \
        -DGEANT4_USE_QT=ON \
        -DGEANT4_USE_QT_QT6=ON \
    && make -j$(nproc) install \
    && cd .. && rm -rf geant4-build geant4-v11.3.2

# ── Step 8.1: Clone OpenTOPAS ─────────────────────────────────────────────────
RUN mkdir -p /root/Applications/TOPAS \
    && cd /root/Applications/TOPAS \
    && git clone https://github.com/OpenTOPAS/OpenTOPAS.git

# ── Step 8.2-8.3: Extract and build GDCM ─────────────────────────────────────
RUN mkdir -p /root/Applications/GDCM \
    && cp /root/Applications/TOPAS/OpenTOPAS/gdcm-2.6.8.tar.gz /root/Applications/GDCM/ \
    && cd /root/Applications/GDCM \
    && tar -zxf gdcm-2.6.8.tar.gz \
    && rm gdcm-2.6.8.tar.gz \
    && mkdir gdcm-build gdcm-install \
    && cd gdcm-build \
    && cmake ../gdcm-2.6.8 \
        -DGDCM_BUILD_SHARED_LIBS=ON \
        -DGDCM_BUILD_DOCBOOK_MANPAGES:BOOL=OFF \
        -DCMAKE_INSTALL_PREFIX=../gdcm-install \
    && make -j$(nproc) install \
    && cd .. && rm -rf gdcm-build gdcm-2.6.8

# ── Step 8.4: Build and install OpenTOPAS ────────────────────────────────────
RUN export Geant4_DIR=/root/Applications/GEANT4/geant4-install \
    && export GDCM_DIR=/root/Applications/GDCM/gdcm-install \
    && cd /root/Applications/TOPAS \
    && mkdir OpenTOPAS-build OpenTOPAS-install \
    && cd OpenTOPAS-build \
    && cmake ../OpenTOPAS \
        -DCMAKE_INSTALL_PREFIX=../OpenTOPAS-install \
        -DCMAKE_PREFIX_PATH=/opt/Qt/6.5.3/gcc_64 \
        -DTOPAS_USE_QT=ON \
        -DTOPAS_USE_QT6=ON \
    && make -j$(nproc) install \
    && cd .. && rm -rf OpenTOPAS-build

# ── Step 9: Set up environment ────────────────────────────────────────────────
ENV QT_QPA_PLATFORM_PLUGIN_PATH=/root/Applications/TOPAS/OpenTOPAS-install/Frameworks
ENV TOPAS_G4_DATA_DIR=/root/Applications/GEANT4/G4DATA
ENV LD_LIBRARY_PATH=/root/Applications/TOPAS/OpenTOPAS-install/lib:/root/Applications/GEANT4/geant4-install/lib:/opt/Qt/6.5.3/gcc_64/lib
ENV PATH=/root/shellScripts:$PATH

# Create convenience `topas` launcher script
RUN mkdir -p /root/shellScripts \
    && printf '#!/bin/bash\nexport QT_QPA_PLATFORM_PLUGIN_PATH=/root/Applications/TOPAS/OpenTOPAS-install/Frameworks\nexport TOPAS_G4_DATA_DIR=/root/Applications/GEANT4/G4DATA\nexport LD_LIBRARY_PATH=/root/Applications/TOPAS/OpenTOPAS-install/lib:$LD_LIBRARY_PATH\nexport LD_LIBRARY_PATH=/root/Applications/GEANT4/geant4-install/lib:$LD_LIBRARY_PATH\n/root/Applications/TOPAS/OpenTOPAS-install/bin/topas "$@"\n' \
        > /root/shellScripts/topas \
    && chmod +x /root/shellScripts/topas \
    && echo 'export PATH=/root/shellScripts:$PATH' >> /root/.bashrc
