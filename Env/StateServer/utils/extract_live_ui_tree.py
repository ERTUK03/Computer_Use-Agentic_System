import shortuuid

_ACTIONABLE = frozenset({"Button", "Edit", "MenuItem", "ListItem", "CheckBox", "TabItem", "Document", "Hyperlink", "TreeItem"})
_STRUCTURAL = frozenset({"ListItem", "Custom", "Group", "Tree", "List", "Pane", "Image", "Tab", "Window", "Toolbar"})

def extract_live_ui_tree(element, global_counts=None, current_depth=0, max_depth=25, get_bounds=False):
    aliases = {}

    def _recur(element, parent_title=None, current_depth=0):
        if current_depth > max_depth:
            return None

        try:
            info = element.element_info
            ctrl_type = info.control_type
            title = (info.name or element.window_text() or "").strip()
        except Exception:
            return None

        # Prune redundant Text nodes that just echo their parent's label
        if ctrl_type == "Text" and title == parent_title:
            return None

        # Duplicate tracking
        match_key = (ctrl_type, title)
        count = global_counts.get(match_key, -1) + 1
        global_counts[match_key] = count
        found_index = count if count != 0 else None

        # Alias long titles
        alias = None
        if len(title) > 100:
            alias = shortuuid.uuid(name=title)
            aliases[alias] = title

        # Build node
        element_data = {"type": ctrl_type}
        if title:
            element_data["title"] = title
        if alias is not None:
            element_data["alias"] = alias
        if found_index is not None:
            element_data["index"] = found_index
        if get_bounds:
            try:
                rect = element.rectangle()
                element_data["bounds"] = [rect.left, rect.top, rect.right, rect.bottom]
            except Exception:
                pass

        # Recurse
        next_depth = current_depth + 1
        child_nodes = []
        if next_depth <= max_depth:
            for child in element.children():
                child_data = _recur(child, parent_title=title, current_depth=next_depth)
                if child_data:
                    child_nodes.append(child_data)

        if child_nodes:
            element_data["children"] = child_nodes
        else:
            if not title and ctrl_type not in _ACTIONABLE:
                return None

        if not title and ctrl_type in _STRUCTURAL:
            return child_nodes or None

        return element_data

    global_counts = global_counts or {}
    return _recur(element, current_depth=current_depth), aliases