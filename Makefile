# Configurable Variables
PYTHON_NAME := python
VENV_NAME := .venv
REQUIREMENTS_FILE_NAME := requirements

# VENV Paths
VENV_PATH_WINDOWS := $(VENV_NAME)\Scripts
VENV_PATH_UNIX := $(VENV_NAME)/bin

# Setup VENV
setup_venv:
ifeq ($(OS),Windows_NT)
	if not exist $(VENV_NAME) $(PYTHON_NAME) -m venv $(VENV_NAME) && \
	$(VENV_PATH_WINDOWS)\python -m pip install --upgrade pip && \
	$(VENV_PATH_WINDOWS)\pip install pipdeptree
else
	test -d $(VENV_NAME) || $(PYTHON_NAME) -m venv $(VENV_NAME) && \
	$(VENV_PATH_UNIX)/python -m pip install --upgrade pip && \
	$(VENV_PATH_UNIX)/pip install pipdeptree
endif

# Install Requirements
install_packages: setup_venv
ifeq ($(OS),Windows_NT)
	$(VENV_PATH_WINDOWS)\pip install -r $(REQUIREMENTS_FILE_NAME).txt && \
	$(VENV_PATH_WINDOWS)\pip freeze > $(REQUIREMENTS_FILE_NAME)_lock.txt && \
	$(VENV_PATH_WINDOWS)\pipdeptree && \
	$(VENV_PATH_WINDOWS)\pipdeptree > pipdeptree.txt
else
	$(VENV_PATH_UNIX)/pip install -r $(REQUIREMENTS_FILE_NAME).txt && \
	$(VENV_PATH_UNIX)/pip freeze > $(REQUIREMENTS_FILE_NAME)_lock.txt && \
	$(VENV_PATH_UNIX)/pipdeptree && \
	$(VENV_PATH_UNIX)/pipdeptree > pipdeptree.txt
endif

# Show Installed Packages
show_packages: setup_venv
ifeq ($(OS),Windows_NT)
	$(VENV_PATH_WINDOWS)\pipdeptree
else
	$(VENV_PATH_UNIX)/pipdeptree
endif

# Uninstall Virtual Environment
clean_venv:
ifeq ($(OS),Windows_NT)
	if exist $(VENV_NAME) rmdir /s /q $(VENV_NAME)
	if exist $(REQUIREMENTS_FILE_NAME)_lock.txt del /q $(REQUIREMENTS_FILE_NAME)_lock.txt
	if exist pipdeptree.txt del /q pipdeptree.txt
else
	test -d $(VENV_NAME) && rm -rf $(VENV_NAME)
	test -f $(REQUIREMENTS_FILE_NAME)_lock.txt && rm -f $(REQUIREMENTS_FILE_NAME)_lock.txt
	test -f pipdeptree.txt && rm -f pipdeptree.txt
endif

# Uninstall Virtual Environment and Install Requirements
clean_install_packages: clean_venv install_packages
