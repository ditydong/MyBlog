
$ErrorActionPreference = "Stop"

# 1. Directory configuration
$Docs = "D:\MyBlog\docs"
$TargetRoot = Join-Path $Docs "dust_dong"

# 2. Allowed file extensions
$AllowedExtensions = @(
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".pdf"
)

# 3. Excluded directories
$ExcludeDirs = @(
    ".obsidian",
    ".trash",
    ".git",
    ([string][char]0x79C1 + [char]0x4EBA),
    ([string][char]0x79C1 + [char]0x5BC6),
    ([string][char]0x65E5 + [char]0x8BB0),
    ([string][char]0x8349 + [char]0x7A3F),
    ([string][char]0x4E34 + [char]0x65F6)
)

# 4. Check source directory
if (-not (Test-Path -LiteralPath $Docs -PathType Container)) {
    throw "Source directory does not exist."
}

# 5. Create destination directory
if (-not (Test-Path -LiteralPath $TargetRoot)) {
    New-Item -ItemType Directory -Path $TargetRoot -Force |
        Out-Null
}

# 6. Initialize counters and conflict list
$Copied = 0
$Same = 0
$Conflicts = @()

$ConflictFile = "D:\MyBlog\merge-conflicts.csv"

# 7. Get all files
$Files = Get-ChildItem -LiteralPath $Docs -Recurse -File -Force

foreach ($File in $Files) {

    # Get relative path
    $RelativePath = $File.FullName.Substring(
        $Docs.TrimEnd('\').Length
    ).TrimStart('\')

    $Segments = $RelativePath -split '[\\/]'

    # Skip existing target directory
    if ($Segments[0] -eq "dust_dong") {
        continue
    }

    # Check excluded directories
    $ShouldExclude = $false

    foreach ($Segment in $Segments) {
        if (
            $Segment.StartsWith(".") -or
            ($ExcludeDirs -contains $Segment)
        ) {
            $ShouldExclude = $true
            break
        }
    }

    if ($ShouldExclude) {
        continue
    }

    # Check file extension
    if (
        $AllowedExtensions -notcontains
        $File.Extension.ToLowerInvariant()
    ) {
        continue
    }

    # Build destination path
    $Target = Join-Path $TargetRoot $RelativePath
    $TargetDir = Split-Path $Target -Parent

    # Create destination directory
    if (-not (Test-Path -LiteralPath $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force |
            Out-Null
    }

    # Copy new files
    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) {
        Copy-Item -LiteralPath $File.FullName `
            -Destination $Target

        $Copied++
        continue
    }

    # Compare file hashes
    $SourceHash = (
        Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256
    ).Hash

    $TargetHash = (
        Get-FileHash -LiteralPath $Target -Algorithm SHA256
    ).Hash

    if ($SourceHash -eq $TargetHash) {
        $Same++
    }
    else {
        # Record conflicts without overwriting files
        $Conflicts += [PSCustomObject]@{
            Source = $File.FullName
            Target = $Target
            SourceHash = $SourceHash
            TargetHash = $TargetHash
        }
    }
}

# 8. Export conflict report
if ($Conflicts.Count -gt 0) {
    $Conflicts | Export-Csv `
        -Path $ConflictFile `
        -NoTypeInformation `
        -Encoding UTF8
}

# 9. Display results
Write-Host "Merge completed." -ForegroundColor Green
Write-Host "New files copied: $Copied"
Write-Host "Identical files skipped: $Same"
Write-Host "Conflicting files: $($Conflicts.Count)"

if ($Conflicts.Count -gt 0) {
    Write-Host "Conflict report: $ConflictFile"
}
