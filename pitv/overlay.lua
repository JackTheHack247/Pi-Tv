-- Pi-TV programme overlay for mpv (colours come from DEFAULT_THEME in pitv/ui/window.py)

local overlay_file = os.getenv("PITV_OVERLAY_FILE") or "/tmp/pitv-overlay.json"
local last_mtime = 0
local overlay = { visible = false }

local DEFAULT_THEME = {
    overlay_bg = "#111111d9",
    overlay_border = "#666666",
    overlay_channel = "#ffffff",
    overlay_program = "#ffffff",
    overlay_description = "#cccccc",
    overlay_muted = "#888888",
    overlay_radius = 10,
}

local MARGIN = 32
local PADDING = 16
local BOX_WIDTH = 420
local BORDER = 2

local function ass_escape(text)
    if not text then
        return ""
    end
    text = tostring(text)
    text = text:gsub("\\", "\\\\")
    text = text:gsub("{", "\\{")
    text = text:gsub("}", "\\}")
    text = text:gsub("\n", "\\N")
    return text
end

local function hex_to_ass(hex)
    hex = (hex or ""):gsub("#", ""):upper()
    if #hex == 8 then
        local rr, gg, bb, aa = hex:sub(1, 2), hex:sub(3, 4), hex:sub(5, 6), hex:sub(7, 8)
        local ass_a = string.format("%02X", 255 - tonumber(aa, 16))
        return string.format("&H%s%s%s%s&", ass_a, bb, gg, rr)
    end
    if #hex == 6 then
        local rr, gg, bb = hex:sub(1, 2), hex:sub(3, 4), hex:sub(5, 6)
        return string.format("&H00%s%s%s&", bb, gg, rr)
    end
    return "&H00FFFFFF&"
end

local function theme_value(theme, key, fallback)
    if theme and theme[key] ~= nil then
        return theme[key]
    end
    return DEFAULT_THEME[key]
end

local function round_rect_path(w, h, r)
    r = math.max(0, math.min(r, math.floor(w / 2), math.floor(h / 2)))
    return string.format(
        "m %d 0 l %d 0 b %d 0 %d %d %d %d l %d %d b %d %d %d %d %d %d l %d %d b %d %d %d %d %d %d l 0 %d b 0 %d %d %d %d %d",
        r,
        w - r,
        w,
        0,
        w,
        r,
        w,
        r,
        w,
        h - r,
        w,
        h,
        w - r,
        h,
        w - r,
        h,
        r,
        h,
        0,
        h,
        0,
        h - r,
        0,
        h - r,
        0,
        r,
        0,
        0,
        r,
        0,
        r,
        r
    )
end

local function count_lines(text)
    if not text or text == "" then
        return 0
    end
    local lines = 1
    for _ in string.gmatch(text, "\n") do
        lines = lines + 1
    end
    return lines
end

local function estimate_box_height(data)
    local height = PADDING * 2 + 34 + 8 + 26
    if data.description and data.description ~= "" then
        height = height + count_lines(data.description) * 22 + 8
    end
    if (data.total or 0) > 0 then
        height = height + 22
    end
    height = height + 20 + PADDING
    return height
end

local function read_overlay()
    local f = io.open(overlay_file, "r")
    if not f then
        return
    end
    local content = f:read("*a")
    f:close()
    if not content or content == "" then
        return
    end
    local ok, parsed = pcall(function()
        return mp.utils.parse_json(content)
    end)
    if ok and parsed then
        overlay = parsed
    end
end

local function render_overlay()
    if not overlay.visible then
        mp.set_osd_ass(0, 0, "")
        return
    end

    local theme = overlay.theme or {}
    local bg = hex_to_ass(theme_value(theme, "overlay_bg", DEFAULT_THEME.overlay_bg))
    local border = hex_to_ass(theme_value(theme, "overlay_border", DEFAULT_THEME.overlay_border))
    local channel_color = hex_to_ass(theme_value(theme, "overlay_channel", DEFAULT_THEME.overlay_channel))
    local program_color = hex_to_ass(theme_value(theme, "overlay_program", DEFAULT_THEME.overlay_program))
    local description_color = hex_to_ass(
        theme_value(theme, "overlay_description", DEFAULT_THEME.overlay_description)
    )
    local muted_color = hex_to_ass(theme_value(theme, "overlay_muted", DEFAULT_THEME.overlay_muted))
    local radius = tonumber(theme_value(theme, "overlay_radius", DEFAULT_THEME.overlay_radius)) or 10

    local channel = ass_escape(overlay.channel or "")
    local program = ass_escape(overlay.program or "")
    local desc = ass_escape(overlay.description or "")
    local idx = overlay.index or 0
    local total = overlay.total or 0

    local box_w = BOX_WIDTH
    local box_h = estimate_box_height(overlay)
    local vid_w = mp.get_property_number("dwidth") or 1280
    local x = math.max(MARGIN, vid_w - MARGIN - box_w)
    local y = MARGIN

    local inner_w = box_w - BORDER * 2
    local inner_h = box_h - BORDER * 2
    local inner_r = math.max(0, radius - BORDER)

    local parts = {
        string.format("{\\p1\\1c%s\\pos(%d,%d)}%s{\\p0}", border, x, y, round_rect_path(box_w, box_h, radius)),
        string.format(
            "{\\p1\\1c%s\\pos(%d,%d)}%s{\\p0}",
            bg,
            x + BORDER,
            y + BORDER,
            round_rect_path(inner_w, inner_h, inner_r)
        ),
        string.format(
            "{\\an7\\pos(%d,%d)\\1c%s\\fs34\\b1}%s{\\b0}",
            x + PADDING,
            y + PADDING,
            channel_color,
            channel
        ),
        string.format(
            "{\\an7\\pos(%d,%d)\\1c%s\\fs26}%s",
            x + PADDING,
            y + PADDING + 42,
            program_color,
            program
        ),
    }

    local text_y = y + PADDING + 42 + 30
    if desc ~= "" then
        table.insert(
            parts,
            string.format("{\\an7\\pos(%d,%d)\\1c%s\\fs20}%s", x + PADDING, text_y, description_color, desc)
        )
        text_y = text_y + count_lines(overlay.description or "") * 22 + 8
    end

    if total > 0 then
        table.insert(
            parts,
            string.format(
                "{\\an7\\pos(%d,%d)\\1c%s\\fs18}Channel %d / %d",
                x + PADDING,
                text_y,
                muted_color,
                idx,
                total
            )
        )
        text_y = text_y + 22
    end

    table.insert(
        parts,
        string.format(
            "{\\an7\\pos(%d,%d)\\1c%s\\fs16}↑↓ change channel  Enter = menu",
            x + PADDING,
            text_y,
            muted_color
        )
    )

    mp.set_osd_ass(0, 0, table.concat(parts, "\\N"))
end

mp.observe_property("time-pos", "number", function()
    local attr = mp.utils.file_info(overlay_file)
    if attr and attr.mtime and attr.mtime ~= last_mtime then
        last_mtime = attr.mtime
        read_overlay()
    end
    render_overlay()
end)

mp.register_event("shutdown", function()
    mp.set_osd_ass(0, 0, "")
end)

read_overlay()
render_overlay()
