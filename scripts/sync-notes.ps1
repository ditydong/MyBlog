$ErrorActionPreference = "Stop"

# 原始 Obsidian 知识库
$Vault = "D:\magic_tool_2\ob_load\dust_dong"

# MkDocs 发布目录
$Docs = "D:\MyBlog\docs"

# 排除的目录名称
$ExcludeDirs = @(
    ".obsidian",
    ".trash",
    ".git",
    "私人",
    "私密",
    "日记",
    "草稿",
    "临时"
)

# 初始允许复制的文件类型
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

# 检查路径
if (!(Test-Path $Vault)) {
    throw "找不到 Obsidian 知识库"
}

if (!(Test-Path $Docs)) {
    New-Item -ItemType Directory -Path $Docs | Out-Null
}

# 遍历原始知识库
$Files = Get-ChildItem -LiteralPath $Vault -Recurse -File -Force

foreach ($File in $Files) {

    # 获取相对路径
    $RelativePath = $File.FullName.Substring(
        $Vault.TrimEnd('\').Length
    ).TrimStart('\')

    $Segments = $RelativePath -split '[\\/]'

    # 排除隐藏目录和私人目录
    if ($Segments | Where-Object {
        $_.StartsWith(".") -or
        $ExcludeDirs -contains $_
    }) {
        continue
    }

    # 只复制允许的文件类型
    if ($AllowedExtensions -notcontains $File.Extension.ToLower()) {
        continue
    }

    # 创建目标目录
    $Target = Join-Path $Docs $RelativePath
    $TargetDir = Split-Path $Target -Parent

    if (!(Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force |
            Out-Null
    }

    # 只复制，不移动、不删除原文件
    Copy-Item -LiteralPath $File.FullName `
        -Destination $Target -Force
}

Write-Host " notee copy right! " -ForegroundColor Green
