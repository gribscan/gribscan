from diagrams import Cluster, Diagram
from diagrams.programming.flowchart import Document, Decision, Database, ManualLoop, Action

with Diagram("magician dataflow", show=False, direction="LR"):
    messages = [Document(f"message {i}") for i in range(1,4)]
    
    with Cluster("for each dataset"):
        with Cluster("for each key"):
            varhook = Action("variable_hook()")
        with Cluster("for each coord"):
            coordhook = Action("coord_hook()")
        m2key = Decision("m2key()")
        (m2key
         >> Database("store by key")
         >> varhook
         >> Action("extra_coords()")
         >> coordhook
         >> Action("globals_hook()")
         >> Document(f"references"))

    messages >> Decision("m2dataset()") >> m2key