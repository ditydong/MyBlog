
$ErrorActionPreference = "Stop"

# 1. Directory configuration
$Vault = "D:\magic_tool_2\ob_load\dust_dong"
$Docs = "D:\MyBlog\docs\dust_dong"

# 2. Excluded directories
# Unicode character codes are used to avoid Chinese encoding issues.
$ExcludeDirs = @(
    ".obsidian",
    ".trash",
    ".git",
    (([char]0x79C1).ToString() + [char]0x4EBA),
    (([char]0x79C1).ToString() + [char]0x5BC6),
    (([char]0x65E5).ToString() + [char]0x8BB0),
    (([char]0x8349).ToString() + [char]0x7A3F),
    (([char]0x4E34).ToString() + [char]0x65F6)
)

# 3. Allowed file extensions
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

# 4. Check source directory
if (-not (Test-Path -LiteralPath $Vault -PathType Container)) {
    throw "Source directory does not exist."
}

# 5. Create destination if necessary
if (-not (Test-Path -LiteralPath $Docs)) {
    New-Item -ItemType Directory -Path $Docs -Force | Out-Null
}

# 6. Read source files
$Files = Get-ChildItem -LiteralPath $Vault -Recurse -File -Force

$CopiedCount = 0
$SkippedCount = 0
$SourceSet = @{}

foreach ($File in $Files) {

    # Get relative path
    $RelativePath = $File.FullName.Substring(
        $Vault.TrimEnd('\').Length
    ).TrimStart('\')

    # Remember every source file, including ones that are not copied,
    # so that stale-file cleanup below never deletes a legitimate copy.
    $SourceSet[$RelativePath.ToLowerInvariant()] = $true

    $Segments = $RelativePath -split '[\\/]'

    # Check excluded directories and hidden files
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
        $SkippedCount++
        continue
    }

    # Check file extension
    if ($AllowedExtensions -notcontains $File.Extension.ToLowerInvariant()) {
        $SkippedCount++
        continue
    }

    # Build destination path
    $Target = Join-Path $Docs $RelativePath
    $TargetDir = Split-Path $Target -Parent

    # Create destination directory
    if (-not (Test-Path -LiteralPath $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force |
            Out-Null
    }

    # Copy only. Never modify source files.
    Copy-Item -LiteralPath $File.FullName `
        -Destination $Target -Force

    $CopiedCount++
}

# 7. Remove files that no longer exist in the vault.
# Without this, renaming or moving a note leaves the old copy behind,
# which is how duplicate pages end up on the site.
$StaleCount = 0
$TargetFiles = Get-ChildItem -LiteralPath $Docs -Recurse -File -Force

foreach ($TargetFile in $TargetFiles) {

    $RelativePath = $TargetFile.FullName.Substring(
        $Docs.TrimEnd('\').Length
    ).TrimStart('\')

    $Segments = $RelativePath -split '[\\/]'

    # Never touch excluded directories or hidden files
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

    # Only consider files this script is responsible for copying
    if (
        $AllowedExtensions -notcontains
        $TargetFile.Extension.ToLowerInvariant()
    ) {
        continue
    }

    if (-not $SourceSet.ContainsKey($RelativePath.ToLowerInvariant())) {
        Remove-Item -LiteralPath $TargetFile.FullName -Force
        $StaleCount++
    }
}

# 8. Remove empty directories left behind by step 7
for ($Pass = 0; $Pass -lt 3; $Pass++) {
    $EmptyDirs = Get-ChildItem -LiteralPath $Docs -Recurse -Directory -Force |
        Where-Object {
            (Get-ChildItem -LiteralPath $_.FullName -Recurse -File -Force |
                Measure-Object).Count -eq 0
        } |
        Sort-Object { $_.FullName.Length } -Descending

    if ($EmptyDirs.Count -eq 0) {
        break
    }

    foreach ($Dir in $EmptyDirs) {
        Remove-Item -LiteralPath $Dir.FullName -Force -Recurse
    }
}

# 9. Display result
Write-Host 'Notes copied successfully.' -ForegroundColor Green
Write-Host "Copied files: $CopiedCount"
Write-Host "Skipped files: $SkippedCount"
Write-Host "Stale files removed: $StaleCount"
