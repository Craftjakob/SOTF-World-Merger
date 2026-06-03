import json
import os
import zipfile


def load_json_from_zip(zip_file, json_name):
    with zip_file.open(json_name, "r") as f:
        return json.load(f)


def open_world(world_path):
    with zipfile.ZipFile(world_path, "r") as zip_f:
        return zip_f, load_json_from_zip(zip_f, "ConstructionsSaveData.json"), load_json_from_zip(zip_f,"FreeFormFreeLinksManagerSaveData.json"), load_json_from_zip(zip_f, "FreeFormStructureLinkerManagerSaveData.json"), load_json_from_zip(zip_f,"ScrewStructureInstancesSaveData.json"), load_json_from_zip(zip_f, "ZipLineManagerSaveData.json")


def merge_worlds(base_world_path, import_world_path, output_world_path):
    base_zip, b_constructions, b_free_form_free_links_manager, b_free_form_structure_linker_manager, b_screw_structure_instances, b_zipline_manager = open_world(base_world_path)
    import_zip, i_constructions, i_free_form_free_links_manager, i_free_form_structure_linker_manager, i_screw_structure_instances, i_zipline_manager = open_world(import_world_path)

    merged_constructions, offsets = merge_constructions(b_constructions, i_constructions)
    merged_free_form_free_links_manager = merge_free_form_free_links_manager(b_free_form_free_links_manager, i_free_form_free_links_manager, offsets)
    merged_free_form_structure_links_manager = merge_free_form_structure_links_manager(b_free_form_structure_linker_manager, i_free_form_structure_linker_manager, offsets)
    merged_screw_structure_instances = merge_screw_structure_instances(b_screw_structure_instances,i_screw_structure_instances)
    merged_zipline_manager = merge_zipline_manager(b_zipline_manager, i_zipline_manager)

    with zipfile.ZipFile(base_world_path, "r") as zin:
        with zipfile.ZipFile(output_world_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:

            for item in zin.infolist():
                buffer = zin.read(item.filename)

                if item.filename == "ConstructionsSaveData.json":
                    buffer = json.dumps(merged_constructions, separators=(",", ":")).encode("utf-8")

                elif item.filename == "FreeFormFreeLinksManagerSaveData.json":
                    buffer = json.dumps(merged_free_form_free_links_manager, separators=(",", ":")).encode("utf-8")

                elif item.filename == "FreeFormStructureLinkerManagerSaveData.json":
                    buffer = json.dumps(merged_free_form_structure_links_manager, separators=(",", ":")).encode("utf-8")

                elif item.filename == "ScrewStructureInstancesSaveData.json":
                    buffer = json.dumps(merged_screw_structure_instances, separators=(",", ":")).encode("utf-8")

                elif item.filename == "ZipLineManagerSaveData.json":
                    buffer = json.dumps(merged_zipline_manager, separators=(",", ":")).encode("utf-8")

                zout.writestr(item, buffer)

    print("Merge completed ->", output_world_path)


def merge_constructions(raw_base, raw_imp):
    base = json.loads(raw_base["Data"]["Constructions"])
    imp = json.loads(raw_imp["Data"]["Constructions"])

    base_structures = base["Structures"]
    imp_structures = imp["Structures"]

    if len(base_structures) != len(imp_structures):
        raise RuntimeError(f"Structures count mismatch: base: {len(base_structures)}, import: {len(imp_structures)}")

    offsets = calculate_offsets(base_structures, imp_structures)
    remap_constructions(imp, offsets)

    for i in range(len(base_structures)):
        if base_structures[i] is None:
            base_structures[i] = []

        if imp_structures[i]:
            base_structures[i].extend(imp_structures[i])

    raw_base["Data"]["Constructions"] = json.dumps(base, separators=(",", ":"))
    return raw_base, offsets


def calculate_offsets(base_structures, import_structures):
    offsets = {}
    for type_id in range(len(base_structures)):
        base_list = base_structures[type_id]
        if base_list is None:
            base_len = 0
        else:
            base_len = len(base_list)

        offsets[type_id] = base_len
    return offsets


def remap_constructions(obj, offsets):
    if isinstance(obj, dict):
        if "TypeID" in obj and "InstanceID" in obj:
            t = obj["TypeID"]
            if t in offsets:
                obj["InstanceID"] += offsets[t]

        for v in obj.values():
            remap_constructions(v, offsets)

    elif isinstance(obj, list):
        for v in obj:
            remap_constructions(v, offsets)


def merge_free_form_free_links_manager(raw_base, raw_imp, offsets):
    base = json.loads(raw_base["Data"]["FreeFormFreeLinksManager"])
    imp = json.loads(raw_imp["Data"]["FreeFormFreeLinksManager"])

    remap_freeform(imp, offsets)

    base["_supportingStructuresData"].extend(imp.get("_supportingStructuresData", []))
    base["_supportedByStructuresData"].extend(imp.get("_supportedByStructuresData", []))
    raw_base["Data"]["FreeFormFreeLinksManager"] = json.dumps(base, separators=(",", ":"))
    return raw_base


def remap_freeform(obj, offsets):
    if isinstance(obj, dict):
        if "_typeId" in obj and "_instanceId" in obj:
            t = obj["_typeId"]
            if t in offsets:
                obj["_instanceId"] += offsets[t]

        for v in obj.values():
            remap_freeform(v, offsets)

    elif isinstance(obj, list):
        for v in obj:
            remap_freeform(v, offsets)


def merge_free_form_structure_links_manager(raw_base, raw_imp, offsets):
    base = json.loads(raw_base["Data"]["FreeFormStructureLinkerManager"])
    imp = json.loads(raw_imp["Data"]["FreeFormStructureLinkerManager"])

    remap_freeform(imp, offsets)

    base["_nodeLinkersData"].extend(imp.get("_nodeLinkersData", []))
    base["_builtLinkersData"].extend(imp.get("_builtLinkersData", []))
    raw_base["Data"]["FreeFormStructureLinkerManager"] = json.dumps(base, separators=(",", ":"))
    return raw_base


def merge_screw_structure_instances(raw_base, raw_imp):
    base = json.loads(raw_base["Data"]["ScrewStructureInstances"])
    imp = json.loads(raw_imp["Data"]["ScrewStructureInstances"])

    base["_structures"].extend(imp["_structures"])
    raw_base["Data"]["ScrewStructureInstances"] = json.dumps(base, separators=(",", ":"))
    return raw_base


def merge_zipline_manager(raw_base, raw_imp):
    base = json.loads(raw_base["Data"]["ZipLineManager"])
    imp = json.loads(raw_imp["Data"]["ZipLineManager"])

    base["Ziplines"].extend(imp["Ziplines"])
    raw_base["Data"]["ZipLineManager"] = json.dumps(base, separators=(",", ":"))
    return raw_base


merge_worlds(
    base_world_path=r"C:\Users\USERNAME\AppData\LocalLow\Endnight\SonsOfTheForest\Saves\STEAM_USER_ID\SinglePlayer\0000000001\SaveData.zip",
    import_world_path=r"C:\Users\USERNAME\AppData\LocalLow\Endnight\SonsOfTheForest\Saves\STEAM_USER_ID\SinglePlayer\0000000002\SaveData.zip",
    output_world_path=r"C:\Users\USERNAME\AppData\LocalLow\Endnight\SonsOfTheForest\Saves\STEAM_USER_ID\SinglePlayer\0000000003\SaveData.zip"
)
