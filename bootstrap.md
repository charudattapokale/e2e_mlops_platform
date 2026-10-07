# Bootstrap: local setup commands (Windows + WSL2 + Docker)

Commands are listed in the order to run them. Each block says where to run it:
**PowerShell** (Windows) or **Ubuntu** (inside WSL2).

If a command fails, check the official docs for that tool, since install steps change between versions.

---

## 1. Check WSL2 (PowerShell)

```powershell
wsl --status
wsl -l -v
```

Expected: `Default Version: 2` and your distribution (for example `Ubuntu`) with `VERSION 2`.

- The line "WSL1 is not supported with your current machine configuration" is harmless. Ignore it.
- If `VERSION` shows `1`: `wsl --set-version Ubuntu 2` (use your distribution's name).

## 2. Install WSL2 only if it is missing (PowerShell as administrator)

Check first that virtualization is enabled: Task Manager, Performance, CPU, "Virtualization: Enabled". If not, enable Intel VT-x or AMD-V/SVM in the BIOS.

```powershell
wsl --install -d Ubuntu-24.04
```

Restart when asked, then create your Linux username and password when Ubuntu opens.

## 3. Limit WSL2 memory (PowerShell, then Notepad)

Create `C:\Users\<your-name>\.wslconfig` (for example `C:\Users\pokal\.wslconfig`). Make sure the file name has no `.txt` extension.

```powershell
notepad C:\Users\pokal\.wslconfig
```

Contents (16 GB laptop; keep `processors` at or below your logical core count):

```ini
[wsl2]
memory=10GB
processors=6
```

Apply it:

```powershell
wsl --shutdown
```

## 4. Open Ubuntu (PowerShell)

```powershell
wsl
```

Your prompt changes to something like `user@laptop:~$`. All commands below run in Ubuntu unless stated.

## 5. Check the Ubuntu version (Ubuntu)

```bash
lsb_release -a
```

"No LSB modules are available" is harmless. Ubuntu 22.04 or 24.04 are both fine.

## 6. Update Ubuntu (Ubuntu)

```bash
sudo apt update && sudo apt upgrade -y
```

- `sudo`: run as administrator
- `apt update`: refresh the list of available packages
- `&&`: run the next command only if the first one worked
- `apt upgrade -y`: install newer versions of installed packages, answering yes automatically

## 7. Check whether Docker is already available (Ubuntu)

```bash
docker --version
which docker
```

- Prints a version: Docker is already there (possibly Docker Desktop with WSL integration). Do not install Docker Engine on top of it. Skip to step 10.
- `command not found`: continue with step 8.

## 8. Install Docker Engine inside Ubuntu (Ubuntu)

Official apt repository method. Do not install this together with Docker Desktop.

```bash
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Let your user run Docker without `sudo`:

```bash
sudo usermod -aG docker $USER
```

Close the Ubuntu window and open it again so the group change applies.

## 9. Start the Docker service

Enable systemd in WSL (Ubuntu):

```bash
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[boot]
systemd=true
EOF
```

Restart WSL (PowerShell):

```powershell
wsl --shutdown
```

Open Ubuntu again (`wsl`) and run:

```bash
sudo systemctl enable --now docker
```

If systemd does not work on your WSL version (`wsl --version` shows it), start Docker manually each time you open Ubuntu:

```bash
sudo service docker start
```

## 10. Test Docker (Ubuntu)

```bash
docker run hello-world
```

Expected: "Hello from Docker!".

## 11. Create the project folder and configure git (Ubuntu)

Keep the project inside the Linux home folder, not under `/mnt/c`. File access is much faster there.

```bash
mkdir -p ~/projects/mlops-platform && cd ~/projects/mlops-platform
git init
git config --global core.autocrlf input
git config --global init.defaultBranch main
```

## 12. Connect the repo to GitHub with SSH (Ubuntu)

Create an empty repo on GitHub first (no README, no `.gitignore`). Set your identity once:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Create an SSH key. At the first prompt ("Enter file in which to save the key") press **Enter** and type nothing. Passphrase is optional.

```bash
ssh-keygen -t ed25519 -C "you@example.com"
cat ~/.ssh/id_ed25519.pub
```

Copy the printed public key (the line starting with `ssh-ed25519`) and add it on GitHub: Settings, SSH and GPG keys, New SSH key. Never share the private key (`id_ed25519` without `.pub`).

Test the connection (type `yes` the first time):

```bash
ssh -T git@github.com
```

Expected: "Hi <user>! You've successfully authenticated, but GitHub does not provide shell access."

Create the first commit, set the remote and push:

```bash
cd ~/projects/mlops-platform

cat > .gitignore <<'EOF'
.terraform/
*.tfstate
*.tfstate.*
*.tfvars
.env
__pycache__/
.venv/
EOF

echo "# mlops-platform" > README.md
git add .
git commit -m "chore: initial commit"
git branch -M main

git remote add origin git@github.com:<user>/<repo>.git
git remote -v
git push -u origin main
```

Fixes:

- Wrong remote address: `git remote set-url origin git@github.com:<user>/<repo>.git`
- `Permission denied (publickey)`: the key is not added to the right GitHub account. Check with `ssh -T git@github.com`, or `ssh -vT git@github.com` for details.
- `rejected ... fetch first`: the GitHub repo was not empty. Run `git pull --rebase origin main`, then push again.

## 13. Install the tools (Ubuntu)

Needs Docker working first (`docker run hello-world`). The tools are `kubectl` (cluster client), `helm` (package manager for Kubernetes), `terraform` (infrastructure as code) and `k3d` (local cluster in Docker).

Check the official install docs of each tool if a command fails, since URLs and versions change.

Run the blocks one at a time, and check the version after each tool before moving on.

### 13a. Base packages

```bash
sudo apt-get update
sudo apt-get install -y make unzip curl gnupg ca-certificates
```

### 13b. kubectl

```bash
curl -fsSLO "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl
```

Check:

```bash
kubectl version --client
```

### 13c. helm

```bash
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

Check:

```bash
helm version
```

### 13d. terraform

```bash
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor --yes -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(. /etc/os-release && echo $VERSION_CODENAME) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list > /dev/null
```

```bash
sudo apt-get update
sudo apt-get install -y terraform
```

Check:

```bash
terraform -version
```

### 13e. k3d

```bash
curl -fsSL https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
```

Check:

```bash
k3d version
```

## 14. Create the local cluster (Ubuntu)

One control-plane node ("server") is enough on a 16 GB laptop.

```bash
k3d cluster create mlops
kubectl get nodes
docker ps
```

Expected: one node in `Ready` state, and a `k3d-mlops-server-0` container in `docker ps`. Check `k3d cluster create --help` for current options.

Delete and recreate it any time:

```bash
k3d cluster delete mlops
k3d cluster create mlops
```

---

## Daily-use commands

| Where | Command | What it does |
| --- | --- | --- |
| PowerShell | `wsl` | Open Ubuntu |
| PowerShell | `wsl -l -v` | List distributions and their state |
| PowerShell | `wsl --shutdown` | Stop WSL completely (also applies `.wslconfig` changes) |
| PowerShell | `wsl --list --online` | Show distributions you can install |
| Ubuntu | `docker ps` | List running containers |
| Ubuntu | `docker stats` | Live memory and CPU use per container |

---

## Where the rest lives

This file is only the one-time setup of a new laptop. The Terraform steps (`init`, `plan`, `apply`, `destroy`) are in `infra/README.md` inside the repo, next to the code they describe.

## Still to add (next steps, not covered yet)

- A `make doctor` target that checks versions, Docker and (later) the GPU
