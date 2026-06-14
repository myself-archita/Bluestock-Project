param(
    [string]$Root = "C:\Users\KIIT\Documents\New project\bluestock_mf_capstone"
)

Add-Type -AssemblyName System.Drawing

function New-Canvas {
    param([string]$Title)
    $bmp = New-Object Drawing.Bitmap 1400, 900
    $g = [Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'AntiAlias'
    $g.Clear([Drawing.Color]::White)
    $titleFont = New-Object Drawing.Font('Segoe UI', 24, [Drawing.FontStyle]::Bold)
    $g.DrawString($Title, $titleFont, [Drawing.Brushes]::Black, 30, 20)
    return @($bmp, $g)
}

function Save-Canvas {
    param($Bmp, $Graphics, [string]$Path)
    $Bmp.Save($Path, [Drawing.Imaging.ImageFormat]::Png)
    $Graphics.Dispose()
    $Bmp.Dispose()
}

function Draw-LineChart {
    param([string]$Path, [string]$Title, $Rows, [string]$XKey, [string]$YKey)
    $canvas = New-Canvas $Title
    $bmp = $canvas[0]
    $g = $canvas[1]
    $font = New-Object Drawing.Font('Segoe UI', 11)
    $x0 = 90; $y0 = 790; $w = 1180; $h = 600
    $g.DrawRectangle([Drawing.Pens]::LightGray, $x0, $y0 - $h, $w, $h)
    $vals = @($Rows | ForEach-Object { [double]($_.$YKey) })
    $min = ($vals | Measure-Object -Minimum).Minimum
    $max = ($vals | Measure-Object -Maximum).Maximum
    if ($max -eq $min) { $max = $min + 1 }
    $sorted = @($Rows | Sort-Object $XKey)
    for ($i = 1; $i -lt $sorted.Count; $i++) {
        $px = $x0 + (($i - 1) * ($w - 10) / [Math]::Max(1, $sorted.Count - 1))
        $py = $y0 - (([double]$sorted[$i-1].$YKey - $min) / ($max - $min) * ($h - 40)) - 20
        $x = $x0 + ($i * ($w - 10) / [Math]::Max(1, $sorted.Count - 1))
        $y = $y0 - (([double]$sorted[$i].$YKey - $min) / ($max - $min) * ($h - 40)) - 20
        $g.DrawLine([Drawing.Pens]::SteelBlue, [int]$px, [int]$py, [int]$x, [int]$y)
    }
    $g.DrawString("Min: $([Math]::Round($min, 2))", $font, [Drawing.Brushes]::Gray, 95, 815)
    $g.DrawString("Max: $([Math]::Round($max, 2))", $font, [Drawing.Brushes]::Gray, 210, 815)
    Save-Canvas $bmp $g $Path
}

function Draw-BarChart {
    param([string]$Path, [string]$Title, $Rows, [string]$LabelKey, [string]$ValueKey)
    $canvas = New-Canvas $Title
    $bmp = $canvas[0]
    $g = $canvas[1]
    $font = New-Object Drawing.Font('Segoe UI', 11)
    $x0 = 100; $y0 = 760; $w = 1200; $h = 560
    $g.DrawRectangle([Drawing.Pens]::LightGray, $x0, $y0 - $h, $w, $h)
    $vals = @($Rows | ForEach-Object { [double]($_.$ValueKey) })
    $max = ($vals | Measure-Object -Maximum).Maximum
    $barW = [int]([Math]::Floor($w / [Math]::Max(1, $Rows.Count))) - 8
    for ($i = 0; $i -lt $Rows.Count; $i++) {
        $row = $Rows[$i]
        $barH = [int](([double]$row.$ValueKey / $max) * ($h - 40))
        $x = $x0 + ($i * ($barW + 8)) + 4
        $y = $y0 - $barH
        $brush = New-Object Drawing.SolidBrush([Drawing.Color]::CornflowerBlue)
        $g.FillRectangle($brush, $x, $y, $barW, $barH)
        $brush.Dispose()
        $g.DrawString([string]$row.$LabelKey, $font, [Drawing.Brushes]::Black, $x, $y0 + 5)
    }
    Save-Canvas $bmp $g $Path
}

function Draw-Pie {
    param([string]$Path, [string]$Title, $Rows, [string]$LabelKey, [string]$ValueKey)
    $canvas = New-Canvas $Title
    $bmp = $canvas[0]
    $g = $canvas[1]
    $rect = New-Object Drawing.Rectangle(140, 140, 500, 500)
    $total = ($Rows | Measure-Object -Property $ValueKey -Sum).Sum
    $start = 0
    $colors = @([Drawing.Brushes]::SteelBlue, [Drawing.Brushes]::Orange, [Drawing.Brushes]::Green, [Drawing.Brushes]::Tomato, [Drawing.Brushes]::Violet, [Drawing.Brushes]::Gold)
    for ($i = 0; $i -lt $Rows.Count; $i++) {
        $slice = 360 * ([double]$Rows[$i].$ValueKey / $total)
        $g.FillPie($colors[$i % $colors.Count], $rect, $start, $slice)
        $start += $slice
    }
    Save-Canvas $bmp $g $Path
}

function Draw-Heatmap {
    param([string]$Path, [string]$Title, $Rows, [string]$XKey, [string]$YKey, [string]$VKey)
    $canvas = New-Canvas $Title
    $bmp = $canvas[0]
    $g = $canvas[1]
    $x0 = 100; $y0 = 780; $cellW = 1100; $cellH = 500
    $xs = @($Rows | Select-Object -ExpandProperty $XKey -Unique | Sort-Object)
    $ys = @($Rows | Select-Object -ExpandProperty $YKey -Unique | Sort-Object)
    $w = [int]($cellW / [Math]::Max(1, $xs.Count))
    $h = [int]($cellH / [Math]::Max(1, $ys.Count))
    $max = ($Rows | Measure-Object -Property $VKey -Maximum).Maximum
    for ($yi = 0; $yi -lt $ys.Count; $yi++) {
        for ($xi = 0; $xi -lt $xs.Count; $xi++) {
            $match = $Rows | Where-Object { $_.$XKey -eq $xs[$xi] -and $_.$YKey -eq $ys[$yi] } | Select-Object -First 1
            if ($match) {
                $v = [double]$match.$VKey
                $t = [int](255 * (1 - ($v / $max)))
                $brush = New-Object Drawing.SolidBrush([Drawing.Color]::FromArgb(255, 255, $t, $t))
                $g.FillRectangle($brush, $x0 + $xi * $w, $y0 - ($yi + 1) * $h, $w - 2, $h - 2)
                $brush.Dispose()
            }
        }
    }
    Save-Canvas $bmp $g $Path
}

$reports = Join-Path $Root 'reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null

$sip = Import-Csv (Join-Path $Root 'data\processed\sip_inflows.csv')
$aum = Import-Csv (Join-Path $Root 'data\processed\aum_growth_by_fund_house.csv')
$folio = Import-Csv (Join-Path $Root 'data\processed\folio_growth.csv')
$geo = Import-Csv (Join-Path $Root 'data\processed\sip_by_state.csv')
$tier = Import-Csv (Join-Path $Root 'data\processed\t30_b30_split.csv')
$dem = Import-Csv (Join-Path $Root 'data\processed\investor_demographics.csv')
$cat = Import-Csv (Join-Path $Root 'data\processed\category_inflows.csv')
$hold = Import-Csv (Join-Path $Root 'data\processed\portfolio_holdings.csv')

Draw-LineChart (Join-Path $reports 'sip_inflow_time_series.png') 'Monthly SIP Inflows' $sip 'month' 'sip_inflow_cr'
Draw-BarChart (Join-Path $reports 'aum_growth_by_fund_house.png') 'AUM Growth by Fund House' ($aum | Where-Object { $_.year -eq '2025' }) 'fund_house' 'aum_cr'
Draw-LineChart (Join-Path $reports 'folio_growth.png') 'Folio Count Growth' $folio 'month' 'folio_cr'
Draw-BarChart (Join-Path $reports 'sip_by_state_barh.png') 'SIP Amount by State' $geo 'state' 'sip_amount'
Draw-Pie (Join-Path $reports 't30_b30_pie.png') 'T30 vs B30 Split' $tier 'city_tier' 'sip_amount'
Draw-Pie (Join-Path $reports 'age_distribution_pie.png') 'Age Group Distribution' (($dem | Group-Object age_group | ForEach-Object { [pscustomobject]@{ age_group = $_.Name; sip_amount = (($_.Group | Measure-Object sip_amount -Sum).Sum) } })) 'age_group' 'sip_amount'
Draw-Heatmap (Join-Path $reports 'category_inflow_heatmap.png') 'Category Inflow Heatmap' $cat 'month' 'category' 'net_inflow_cr'
Draw-Pie (Join-Path $reports 'gender_split.png') 'Gender Split' (($dem | Group-Object gender | ForEach-Object { [pscustomobject]@{ gender = $_.Name; sip_amount = (($_.Group | Measure-Object sip_amount -Sum).Sum) } })) 'gender' 'sip_amount'
Draw-Pie (Join-Path $reports 'sector_allocation_donut.png') 'Sector Allocation' $hold 'sector' 'weight_pct'

$placeholders = @('nav_return_correlation_heatmap.png','benchmark_overlay.png','nav_trend_all_schemes.png','monthly_return_trend.png','volatility_rank.png','top_categories.png','return_distribution.png','investor_pie_age.png','city_tier_pie.png','state_bar.png')
foreach ($name in $placeholders) {
    $canvas = New-Canvas $name
    $bmp = $canvas[0]
    $g = $canvas[1]
    $font = New-Object Drawing.Font('Segoe UI', 16)
    $g.DrawRectangle([Drawing.Pens]::LightGray, 80, 120, 1200, 600)
    $g.DrawString('Placeholder chart rendered from sample data or awaiting the source CSV.', $font, [Drawing.Brushes]::Gray, 100, 170)
    Save-Canvas $bmp $g (Join-Path $reports $name)
}
