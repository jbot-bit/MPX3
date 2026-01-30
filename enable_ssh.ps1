# Enable SSH Server on Windows
# Run this script as Administrator

Write-Host "Installing OpenSSH Server..." -ForegroundColor Cyan

# Install OpenSSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

Write-Host "`nStarting SSH service..." -ForegroundColor Cyan

# Start the SSH service
Start-Service sshd

# Set SSH to start automatically
Set-Service -Name sshd -StartupType 'Automatic'

Write-Host "`nConfiguring Windows Firewall..." -ForegroundColor Cyan

# Configure Windows Firewall (check if rule already exists)
$firewallRule = Get-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue
if (-not $firewallRule) {
    New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
    Write-Host "Firewall rule created" -ForegroundColor Green
} else {
    Write-Host "Firewall rule already exists" -ForegroundColor Yellow
}

Write-Host "`n=== SSH Server Status ===" -ForegroundColor Green
Get-Service sshd | Select-Object Name, Status, StartType

Write-Host "`n=== Your Connection Details ===" -ForegroundColor Green
$ipAddresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } | Select-Object -ExpandProperty IPAddress
Write-Host "IP Addresses: $($ipAddresses -join ', ')"
Write-Host "Port: 22"
Write-Host "Username: $env:USERNAME"

Write-Host "`nSSH Server is now running!" -ForegroundColor Green
Write-Host "Connect using: ssh $env:USERNAME@<your-ip-address>" -ForegroundColor Cyan

pause
