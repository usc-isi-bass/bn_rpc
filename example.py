import os
from binaryninja import *
os.chdir(os.path.dirname(os.path.realpath(__file__)))
bv = BinaryViewType.get_view_of_file("func.out")
for func in bv.functions:
    print("== Func: %s ==" % func.symbol.full_name)
    print("== LLIL:")
    for idx in range(len(func.llil)):
        print("\t%s" % func.llil[idx])
    print("== MLIL:")
    for idx in range(len(func.mlil)):
        print("\t%s" % func.mlil[idx])
