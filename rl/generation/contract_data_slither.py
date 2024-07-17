import os
import solcx
from slither import Slither

from slither.core.solidity_types import UserDefinedType, MappingType, \
   ElementaryType, ArrayType
import logging
logger=logging.getLogger(__name__)

def get_contract_from_slither(solidity_file_path:str,solidity_file_name:str,contract_name:str, solc_version:str="0.4.25"):

    if len(solc_version)==0:
        solc_version="0.4.24"

    if solc_version not in solcx.get_installed_solc_versions():
        solcx.install_solc(solc_version)
    solcx.set_solc_version(solc_version)

    solc_path = str(solcx.get_solcx_install_folder()) + "\solc-v{}\solc.exe".format(solc_version)
    if not os.path.exists(solc_path):
        logger.error(f"Does not exist: {solc_path}")
        print(f"Does not exist: {solc_path}")
        return None
    solidity_file_path_name=solidity_file_path+solidity_file_name

    if os.path.exists(solidity_file_path_name):
        try:
            contract=None
            # Init slither
            slither = Slither(solidity_file_path_name, solc=solc_path)

            # Get the contract
            contracts = slither.get_contract_from_name(contract_name=contract_name)
            assert len(contracts) == 1
            contract = contracts[0]

        except:
            print('have exception when getting slither contract')
        finally:
            return contract
    else:
        logger.error(f"Does not exist: {solidity_file_path_name}")
        print(f"Does not exist: {solidity_file_path_name}")
        return None


def get_rw_data_from_slither(solidity_file_path:str,solidity_file_name:str,contract_name:str, solc_version:str="0.4.25"):
    contract = get_contract_from_slither(solidity_file_path,
                                         solidity_file_name, contract_name,
                                         solc_version)

    svar_names = []
    svar_initialized = []
    svar_constants = []
    svar_type={}
    if contract is None:
        return [],[],{},{}
    # collect all state variables
    state_variables = contract.state_variables
    for sv in contract.all_state_variables_written + contract.all_state_variables_read:
        if sv not in state_variables:
            state_variables.append(sv)

    for sv in state_variables:
        name = sv.name
        if sv.is_constant:
            svar_constants.append(name)
        if sv.initialized:
            if name not in svar_constants:
                svar_initialized.append(name)

        #--------------------------
        # change type names
        if isinstance(sv.type, UserDefinedType):
            tp = 'userDefined'
        elif sv.type.is_dynamic:
            tp = 'dynamic'
            if isinstance(sv.type, MappingType):
                if isinstance(sv.type.type_to, ElementaryType):
                    tp = 'mapping1'
                elif isinstance(sv.type.type_to, MappingType):
                    tp = 'mapping2'
                elif isinstance(sv.type.type_to, ArrayType):
                    tp = 'mapping2'
                elif isinstance(sv.type.type_to, UserDefinedType):
                    tp = 'mapping3'
                else:
                    pass
            elif isinstance(sv.type, ElementaryType):
                # string,bytes
                tp = str(sv.type)
                # print(f'dynamic:{tp} (contract_data_slither.py)')
            elif isinstance(sv.type, ArrayType):
                if isinstance(sv.type.type, ElementaryType):
                    tp = 'array1'
                elif isinstance(sv.type.type, ArrayType):
                    tp = 'array2'
                elif isinstance(sv.type.type, MappingType):
                    tp = 'array2'
                elif isinstance(sv.type.type, UserDefinedType):
                    tp = 'array3'
                else:
                    pass
            else:
                pass

        else:

            if str(sv.type).startswith('bytes') and len(str(sv.type)) > 5:
                if isinstance(sv.type, ArrayType):
                    tp = 'array_bytesFixed'
                else:
                    tp = 'bytesFixed'
            elif str(sv.type).startswith('uint256'):
                if isinstance(sv.type, ArrayType):
                    tp = 'array_uint256'
                else:
                    tp = 'uint256'
            elif str(sv.type).startswith('uint'):
                if isinstance(sv.type, ArrayType):
                    tp = 'array_uintSmall'
                else:
                    tp = 'uintSmall'
            elif str(sv.type).startswith('int'):
                if isinstance(sv.type, ArrayType):
                    tp = 'array_int'
                else:
                    tp = 'int'
            elif str(sv.type).startswith('address'):
                if isinstance(sv.type, ArrayType):
                    tp = 'array_address'
                else:
                    tp = 'address'
            elif str(sv.type).startswith('bool'):
                if isinstance(sv.type, ArrayType):
                    tp = 'array_bool'
                else:
                    tp = 'bool'
            elif str(sv.type).startswith('float'):
                if isinstance(sv.type, ArrayType):
                    tp = 'array_float'
                else:
                    tp = 'float'
            else:
                if '[' in str(sv.type) and ']' in str(sv.type):
                    tp = 'array_extra'
                else:
                    tp = str(sv.type)
        #-------------- end -----------------
        if name not in svar_constants:
            svar_names.append(str(name))
            svar_type[name]=tp



    function_r_w = {}
    for function in contract.functions:
        flag_constructor = False
        # do not consider constructor
        if function.is_constructor:
            flag_constructor = True

        # only consider public and external functions which can be invoked by users.
        if function.visibility not in ['public', 'external']: continue

        # do not consider the functions of public state variables
        pure_name = function.name
        if pure_name in svar_names: continue

        sv_read_in_condition_1 = function.all_conditional_state_variables_read()
        sv_read_in_condition_1_0 = [sv.name for sv in sv_read_in_condition_1 if
                                    sv.name not in svar_constants]

        sv_written = [sv.name for sv in function.all_state_variables_written()
                      if sv.name not in svar_constants]

        if flag_constructor:
            if 'constructor' in function_r_w.keys():
                sv_read_in_condition_1_0 = function_r_w['constructor'][
                                               'reads'] + sv_read_in_condition_1_0
                sv_written = function_r_w['constructor']['writes'] + sv_written

            function_r_w['constructor'] = {
                "reads": sv_read_in_condition_1_0,
                "writes": sv_written + svar_initialized,
            }
        else:
            function_r_w[function.canonical_name] = {
                "reads": sv_read_in_condition_1_0,
                "writes": sv_written,
            }
    if 'constructor' not in function_r_w.keys():
        function_r_w['constructor'] = {
            "reads": [],
            "writes": svar_initialized,
        }

    return  svar_names, svar_constants,svar_type,function_r_w
