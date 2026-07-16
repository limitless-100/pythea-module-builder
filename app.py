import streamlit as st
import graphviz
import json

# Import your backend logic
# (Assuming ClinicalStates.py is in the same folder)
try:
    from ClinicalStates import ConditionOnset, Encounter, EncounterEnd, Procedure
    from transitions import direct_transition, distributed_transition
except ImportError:
    st.error("Make sure ClinicalStates.py and transitions.py are in the same folder as app.py")

def generate_baseline_module():
    """Generates the starting dataset for the hackathon (e.g., Malaria/Typhoid)."""
    states = {}

    # 1. Initial State (Required by Synthea)
    states["Initial"] = {
        "type": "Initial",
        "direct_transition": "Malaria_Onset"
    }

    # 2. Condition Onset
    onset = ConditionOnset("Malaria_Onset", codes=[{"system": "SNOMED-CT", "code": "61462000", "display": "Malaria"}])
    onset.apply_transition(direct_transition("Malaria_Onset", "ConditionOnset", "Clinic_Visit"))
    states.update(onset.build())

    # 3. Encounter
    encounter = Encounter("Clinic_Visit", encounter_class="ambulatory", codes=[{"system": "SNOMED-CT", "code": "185349003"}])
    encounter.apply_transition(distributed_transition(
        "Clinic_Visit", "Encounter", 
        distribution=[0.7, 0.3], 
        distributed_states=["Cured_Terminal", "Relapse_Terminal"]
    ))
    states.update(encounter.build())

    # 4. Terminals
    states["Cured_Terminal"] = {"type": "Terminal"}
    states["Relapse_Terminal"] = {"type": "Terminal"}

    return states

def build_visual_graph(states_dict):
    """Parses the Synthea JSON dictionary and generates a Graphviz DOT object."""
    dot = graphviz.Digraph(comment='Synthea Module')
    dot.attr(rankdir='TB', size='8,8') # Top to Bottom layout

    # Color mapping for different state types
    colors = {
        "Initial": "lightgreen",
        "Terminal": "lightpink",
        "ConditionOnset": "lightyellow",
        "Encounter": "lightblue",
        "Procedure": "thistle",
        "ConditionEnd": "moccasin"
    }

    # 1. Create all nodes
    for state_name, state_data in states_dict.items():
        state_type = state_data.get("type", "Unknown")
        color = colors.get(state_type, "white")
        
        # Format the label (Bold name, italic type)
        label = f'<<B>{state_name}</B><BR/><I>{state_type}</I>>'
        dot.node(state_name, label=label, style='filled', fillcolor=color, shape='box', rounded='true')

    # 2. Draw all edges (Transitions)
    for state_name, state_data in states_dict.items():
        # Direct Transitions
        if "direct_transition" in state_data:
            dot.edge(state_name, state_data["direct_transition"])
            
        # Distributed Transitions
        elif "distribution_transition" in state_data:
            for dist in state_data["distribution_transition"]:
                prob = str(int(dist["distribution"] * 100)) + "%"
                dot.edge(state_name, dist["transition"], label=prob)
                
        # Conditional Transitions
        elif "conditional_transition" in state_data:
            for cond in state_data["conditional_transition"]:
                cond_val = cond.get("condition", {}).get("condition", "condition")
                dot.edge(state_name, cond["transition"], label=cond_val, style='dashed')

    return dot

# ==========================================
# STREAMLIT UI LAYOUT
# ==========================================
st.set_page_config(page_title="Synthea Builder - Nigeria", layout="wide")

# Initialize session state so data persists between button clicks
if 'module_states' not in st.session_state:
    st.session_state.module_states = generate_baseline_module()

st.title("🇳🇬 Synthea MVP Builder - Nigeria Context")

# Sidebar for controls
with st.sidebar:
    st.header("Module Controls")
    
    if st.button("Reset to Baseline Malaria Path"):
        st.session_state.module_states = generate_baseline_module()
        st.success("Reset successful!")
        
    st.divider()
    st.write("*(For the next sprint phase, we will add 'Add New State' dynamic forms here)*")

# Main Content Area
tab1, tab2 = st.tabs(["Visual Canvas", "JSON Export"])

with tab1:
    st.subheader("Module Flowchart")
    # Generate and render the Graphviz object
    graph = build_visual_graph(st.session_state.module_states)
    st.graphviz_chart(graph)

with tab2:
    st.subheader("Synthea Compliant JSON")
    
    # Wrap it in the official Synthea root structure
    final_json = {
        "name": "Nigeria_Malaria_MVP",
        "remarks": [ "Built during 48hr hackathon" ],
        "states": st.session_state.module_states
    }
    
    json_string = json.dumps(final_json, indent=4)
    st.code(json_string, language="json")
    
    # Download Button
    st.download_button(
        label="Download Module JSON",
        file_name="nigeria_malaria_module.json",
        mime="application/json",
        data=json_string
    )
