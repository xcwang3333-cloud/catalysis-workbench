param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$ExpectedFileName,
    [Parameter(Mandatory = $true)][string]$PublisherSubjectRegex,
    [string]$ExpectedSha256 = "",
    [switch]$RequireTimestamp
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$resolved = (Resolve-Path -LiteralPath $Path).Path
$item = Get-Item -LiteralPath $resolved
if ($item.PSIsContainer) {
    throw "Signed artifact path is a directory: $resolved"
}
if ($item.Name -cne $ExpectedFileName) {
    throw "Signed artifact filename drift: expected '$ExpectedFileName', got '$($item.Name)'"
}

$signature = Get-AuthenticodeSignature -FilePath $resolved
if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Authenticode signature is not valid: $($signature.Status) $($signature.StatusMessage)"
}
if ($null -eq $signature.SignerCertificate) {
    throw "Authenticode signer certificate is missing"
}
if ($signature.SignerCertificate.Subject -notmatch $PublisherSubjectRegex) {
    throw "Unexpected signer subject: $($signature.SignerCertificate.Subject)"
}

$isSelfSigned = $signature.SignerCertificate.Subject -eq $signature.SignerCertificate.Issuer
if ($isSelfSigned) {
    throw "Self-signed certificates are not accepted for publication"
}

$codeSigningOid = "1.3.6.1.5.5.7.3.3"
$ekuOids = @()
foreach ($extension in $signature.SignerCertificate.Extensions) {
    if ($extension.Oid.Value -eq "2.5.29.37") {
        $eku = [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]$extension
        foreach ($oid in $eku.EnhancedKeyUsages) {
            $ekuOids += $oid.Value
        }
    }
}
if ($ekuOids -notcontains $codeSigningOid) {
    throw "Signer certificate is missing the Code Signing EKU ($codeSigningOid)"
}

if ($RequireTimestamp -and $null -eq $signature.TimeStamperCertificate) {
    throw "RFC3161/AuthentiCode timestamp certificate is missing"
}

$sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolved).Hash.ToLowerInvariant()
if ($ExpectedSha256) {
    $expected = $ExpectedSha256.Trim().ToLowerInvariant()
    if ($sha256 -ne $expected) {
        throw "Signed artifact SHA-256 drift: expected $expected, got $sha256"
    }
}

$timestamp = $null
if ($null -ne $signature.TimeStamperCertificate) {
    $timestamp = [ordered]@{
        subject = $signature.TimeStamperCertificate.Subject
        thumbprint = $signature.TimeStamperCertificate.Thumbprint
        not_before = $signature.TimeStamperCertificate.NotBefore.ToUniversalTime().ToString("o")
        not_after = $signature.TimeStamperCertificate.NotAfter.ToUniversalTime().ToString("o")
    }
}

$result = [ordered]@{
    schema_version = 1
    path = $resolved
    filename = $item.Name
    sha256 = $sha256
    signature_status = $signature.Status.ToString()
    signer = [ordered]@{
        subject = $signature.SignerCertificate.Subject
        issuer = $signature.SignerCertificate.Issuer
        thumbprint = $signature.SignerCertificate.Thumbprint
        self_signed = $isSelfSigned
        not_before = $signature.SignerCertificate.NotBefore.ToUniversalTime().ToString("o")
        not_after = $signature.SignerCertificate.NotAfter.ToUniversalTime().ToString("o")
    }
    timestamp = $timestamp
}

$result | ConvertTo-Json -Depth 5
