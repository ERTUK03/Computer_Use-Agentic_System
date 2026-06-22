from ...utils.load_model import load_full_model

def get_planner(hooks=None):
    model_name = "planner"

    planner = load_full_model(
        model_name,
        capabilities = hooks,
        include_prompt=True
    )
    
    return planner