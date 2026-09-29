Add-Type -AssemblyName System.Drawing

$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($id in @('mini', 'sentry', 'charger', 'shield', 'floater')) {
    $path = Join-Path $folder "${id}_turnaround.png"
    $source = [System.Drawing.Bitmap]::new($path)
    try {
        if ($source.Width -eq 4096 -and $source.Height -eq 2048) { continue }
        $target = [System.Drawing.Bitmap]::new(4096, 2048, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($target)
            try {
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
                $graphics.DrawImage($source, 0, 0, 4096, 2048)
            } finally { $graphics.Dispose() }
            $temp = Join-Path $folder "${id}_turnaround.resized.png"
            $target.Save($temp, [System.Drawing.Imaging.ImageFormat]::Png)
        } finally { $target.Dispose() }
    } finally { $source.Dispose() }
    Move-Item -LiteralPath $temp -Destination $path -Force
    Write-Output "RESIZED $id 4096x2048"
}
