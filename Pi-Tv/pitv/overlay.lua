-- Pi-TV top-right channel / programme overlay for mpv

local overlay_file = os.getenv("PITV_OVERLAY_FILE") or "/tmp/pitv-overlay.json"
local last_mtime = 0
local overlay = { visible = false }

local function read_overlay()
    local f = io.open(overlay_file, "r")
    if not f then
        return
    end
    local data = f:read("*a")
    f:close()
    if not data or data == "" then
        return
    end
    local ok, parsed = pcall(function()
        -- mpv ships with a JSON parser via mp.utils
        return mp.utils.parse_json(data)
    end)
    if ok and parsed then
        overlay = parsed
    end
end

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

local function render_overlay()
    if not overlay.visible then
        mp.set_osd_ass(0, 0, "")
        return
    end

    local channel = ass_escape(overlay.channel or "")
    local program = ass_escape(overlay.program or "")
    local desc = ass_escape(overlay.description or "")
    local idx = overlay.index or 0
    local total = overlay.total or 0

    local lines = {
        "{\\an9}",
        "{\\fs34\\b1}" .. channel .. "{\\b0}",
        "{\\fs26}" .. program,
    }

    if desc ~= "" then
        table.insert(lines, "{\\fs20}" .. desc)
    end

    if total > 0 then
        table.insert(lines, "{\\fs18\\alpha&H80&}Channel " .. idx .. " / " .. total)
    end

    table.insert(lines, "{\\fs16\\alpha&H60&}↑↓ change channel  Enter = country menu")

    mp.set_osd_ass(0, 0, table.concat(lines, "\\N"))
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
