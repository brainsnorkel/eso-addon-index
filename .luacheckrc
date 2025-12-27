-- ESO Addon Luacheck Configuration
-- Used for validating addon source code quality

std = "lua51"
max_line_length = 200

-- ESO global functions and namespaces
globals = {
    -- Core managers
    "SLASH_COMMANDS",
    "EVENT_MANAGER",
    "SCENE_MANAGER",
    "CALLBACK_MANAGER",
    "WINDOW_MANAGER",
    "ANIMATION_MANAGER",
    "CHAT_SYSTEM",
    "LINK_HANDLER",

    -- Common libraries
    "LibAddonMenu2",
    "LibStub",
    "LibDebugLogger",
    "LibCustomMenu",

    -- ZO functions that modify state
    "ZO_SavedVars",
    "ZO_Dialogs_ShowDialog",
    "ZO_Dialogs_RegisterCustomDialog",
    "ZO_Dialogs_ReleaseDialog",
    "ZO_CreateStringId",
    "ZO_PreHook",
    "ZO_PostHook",
    "ZO_PreHookHandler",
    "ZO_PostHookHandler",

    -- Debug output
    "d",
    "df",
    "CHAT_ROUTER",
}

read_globals = {
    -- ESO API (common functions)
    "GetAPIVersion",
    "GetESOVersionString",
    "GetDisplayName",
    "GetRawUnitName",
    "GetUnitName",
    "GetUnitDisplayName",
    "GetMapPlayerPosition",
    "GetCurrentMapZoneIndex",
    "GetCurrentMapId",
    "GetGameTimeMilliseconds",
    "GetFrameTimeMilliseconds",
    "GetFrameTimeSeconds",
    "GetTimeStamp",
    "GetDiffBetweenTimeStamps",
    "GetString",
    "GetControl",
    "CreateControl",
    "CreateControlFromVirtual",
    "CreateTopLevelWindow",
    "PlaySound",
    "SOUNDS",

    -- Unit functions
    "IsUnitInCombat",
    "IsUnitPlayer",
    "IsUnitGrouped",
    "IsUnitDead",
    "IsUnitOnline",
    "GetUnitClass",
    "GetUnitClassId",
    "GetUnitRace",
    "GetUnitRaceId",
    "GetUnitLevel",
    "GetUnitEffectiveLevel",
    "GetUnitChampionPoints",
    "GetUnitPower",
    "GetUnitZone",
    "DoesUnitExist",
    "AreUnitsEqual",

    -- Buff/Effect functions
    "GetNumBuffs",
    "GetUnitBuffInfo",
    "GetAbilityName",
    "GetAbilityIcon",
    "GetAbilityDuration",
    "GetAbilityId",
    "DoesAbilityExist",

    -- Combat functions
    "GetSlotCooldownInfo",
    "GetSlotBoundId",
    "IsSlotUsed",
    "GetActiveHotbarCategory",

    -- Group functions
    "GetGroupSize",
    "GetGroupMemberIndexFromUnitTag",
    "GetGroupUnitTagByIndex",
    "IsUnitGroupLeader",
    "IsInRaid",
    "GetRaidMemberPartyRole",

    -- Map functions
    "GetMapTileTexture",
    "GetCurrentMapIndex",
    "GetMapNameById",

    -- Common ZO_ functions
    "ZO_ColorDef",
    "ZO_Anchor",
    "ZO_Object",
    "ZO_InitializingObject",
    "zo_strformat",
    "zo_strlower",
    "zo_strupper",
    "zo_strlen",
    "zo_strsub",
    "zo_strtrim",
    "zo_strmatch",
    "zo_strsplit",
    "zo_min",
    "zo_max",
    "zo_clamp",
    "zo_round",
    "zo_roundToNearest",
    "zo_floor",
    "zo_ceil",
    "zo_abs",
    "zo_sign",
    "zo_lerp",
    "zo_percentBetween",
    "zo_plainTableCopy",
    "zo_shallowTableCopy",
    "zo_deepTableCopy",
    "zo_mixin",
    "zo_callLater",
    "zo_removeCallLater",
    "zo_callHandler",
    "zo_iconFormat",
    "zo_iconTextFormat",
    "zo_iconTextFormatNoSpace",

    -- Events (partial list - add more as needed)
    "EVENT_ADD_ON_LOADED",
    "EVENT_PLAYER_ACTIVATED",
    "EVENT_PLAYER_DEACTIVATED",
    "EVENT_RETICLE_TARGET_CHANGED",
    "EVENT_EFFECT_CHANGED",
    "EVENT_COMBAT_EVENT",
    "EVENT_PLAYER_COMBAT_STATE",
    "EVENT_UNIT_DEATH_STATE_CHANGED",
    "EVENT_POWER_UPDATE",
    "EVENT_BOSSES_CHANGED",
    "EVENT_ZONE_CHANGED",
    "EVENT_COLLECTIBLE_UPDATED",
    "EVENT_ACTION_SLOT_UPDATED",
    "EVENT_ACTION_SLOTS_ALL_HOTBARS_UPDATED",
    "EVENT_ACTIVE_QUICKSLOT_CHANGED",
    "EVENT_INVENTORY_SINGLE_SLOT_UPDATE",
    "EVENT_INVENTORY_FULL_UPDATE",
    "EVENT_EXPERIENCE_UPDATE",
    "EVENT_CHAMPION_POINT_GAINED",
    "EVENT_PLAYER_DEAD",
    "EVENT_PLAYER_ALIVE",
    "EVENT_TARGET_CHANGED",

    -- Action results
    "ACTION_RESULT_ABILITY_ON_COOLDOWN",
    "ACTION_RESULT_BLOCKED",
    "ACTION_RESULT_BLOCKED_DAMAGE",
    "ACTION_RESULT_CRITICAL_DAMAGE",
    "ACTION_RESULT_CRITICAL_HEAL",
    "ACTION_RESULT_DAMAGE",
    "ACTION_RESULT_DAMAGE_SHIELDED",
    "ACTION_RESULT_DODGED",
    "ACTION_RESULT_DOT_TICK",
    "ACTION_RESULT_DOT_TICK_CRITICAL",
    "ACTION_RESULT_EFFECT_GAINED",
    "ACTION_RESULT_EFFECT_FADED",
    "ACTION_RESULT_HEAL",
    "ACTION_RESULT_HOT_TICK",
    "ACTION_RESULT_HOT_TICK_CRITICAL",
    "ACTION_RESULT_IMMUNE",
    "ACTION_RESULT_MISS",
    "ACTION_RESULT_PARRIED",
    "ACTION_RESULT_POWER_DRAIN",
    "ACTION_RESULT_POWER_ENERGIZE",
    "ACTION_RESULT_REFLECTED",
    "ACTION_RESULT_RESIST",
    "ACTION_RESULT_REINCARNATING",

    -- UI anchors
    "CENTER",
    "TOP",
    "BOTTOM",
    "LEFT",
    "RIGHT",
    "TOPLEFT",
    "TOPRIGHT",
    "BOTTOMLEFT",
    "BOTTOMRIGHT",

    -- UI globals
    "GuiRoot",
    "ZO_WorldMap",
    "ZO_WorldMapScroll",
    "ZO_CompassFrame",

    -- SI strings (localization)
    "SI_BINDING_NAME_",

    -- Miscellaneous
    "GetCVar",
    "SetCVar",
    "RequestOpenMailbox",
    "GetCurrentZoneHouseId",
    "GetHousingPrimaryHouse",
    "IsInGamepadPreferredMode",
    "IsConsoleUI",
}

-- Ignore common ESO patterns
ignore = {
    "212",  -- Unused argument (common in event handlers)
    "213",  -- Unused loop variable
    "311",  -- Value assigned to variable is unused (common pattern)
    "542",  -- Empty if branch (sometimes intentional)
}

-- File-specific overrides
files["**/lang/*.lua"] = {
    -- Localization files often have unused strings
    ignore = {"111", "112", "113"},
}
