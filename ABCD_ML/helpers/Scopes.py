from .ML_Helpers import conv_to_list
from ..pipeline.Input_Tools import is_scope

class Scopes():

    def __init__(self, data_keys, data_file_keys,
                 cat_keys, strat_keys, covars_keys,
                 covar_scopes, cat_encoders,
                 file_mapping=None):
        '''Class to hold and handle the different scope level / all keys type fields'''

        self.data_keys = data_keys
        self.data_file_keys = data_file_keys
        self.cat_keys = cat_keys
        self.strat_keys = strat_keys
        self.covars_keys = covars_keys
        self.covar_scopes = covar_scopes
        self.cat_encoders = cat_encoders

        if file_mapping is None:
            file_mapping = {}
        self.file_mapping = file_mapping

    def set_all_keys(self, scope, targets_key):
    
        # To start set all_keys with everything
        self.keys_at_end = self.strat_keys + conv_to_list(targets_key)

        self.all_keys =\
            self.data_keys + self.covars_keys + self.keys_at_end

        # Filter all_keys by scope, and set new all keys
        scoped_keys = self.get_keys_from_scope(scope)
        self.all_keys = scoped_keys + self.keys_at_end

        # Target key(s) should always be last in all_keys!

        # Store total number of valid keys
        self.num_feat_keys = len(self.all_keys) - len(self.keys_at_end)

    def get_keys_from_scope(self, scope_obj):

        if is_scope(scope_obj):
            scope = scope_obj.value
        else:
            scope = scope_obj

        from ..helpers.VARS import SCOPES
        
        if isinstance(scope, str) and scope in SCOPES:

            if scope == 'float':
                keys = [k for k in self.all_keys if k not in self.cat_keys]

            elif scope == 'data':
                keys = self.data_keys.copy()

            elif scope == 'data files':
                keys = self.data_file_keys.copy()

            elif scope == 'float covars' or scope == 'fc':
                keys = [k for k in self.all_keys if
                        k not in self.cat_keys and
                        k not in self.data_keys]

            elif scope == 'all' or scope == 'n':
                keys = self.all_keys.copy()

            elif scope == 'cat' or scope == 'categorical':
                keys = self.cat_keys.copy()

            elif scope == 'covars':
                keys = self.covars_keys.copy()

            else:
                print('Should never reach here.')
                pass

        # If not a valid passed scope, should be list like
        else:

            scope = conv_to_list(scope)
            
            keys, restrict_keys = [], []
            for key in scope:

                # If a valid scope, add to keys
                if key in SCOPES:
                    keys += self.get_keys_from_scope(key)
                
                # If a passed column name, add to keys
                elif key in self.all_keys:
                    keys.append(key)
                
                # Otherwise append to restrict keys
                else:
                    restrict_keys.append(key)

            # Restrict all keys by the stub strs passed that arn't scopes or valid column names
            if len(restrict_keys) > 0:
                keys += [a for a in self.all_keys if all([r in a for r in restrict_keys])]
            
            # Get rid of repeats if any
            keys = list(set(keys))
        
        # Need to remove all strat keys + target_keys, if there regardless
        for key in self.keys_at_end:
            
            try:
                keys.remove(key)
            except ValueError:
                pass

        return keys

    def get_train_inds_from_keys(self, keys):
        '''Assume target is always last within self.all_keys ...
        maybe a bad assumption.'''

        inds = [self.all_keys.index(k) for k in keys if k in self.all_keys]
        return inds

    def get_inds_from_scope(self, scope):
        '''Return inds from scope'''

        # First get keys from scope
        keys = self.get_keys_from_scope(scope)

        # Then change to inds
        inds = self.get_train_inds_from_keys(keys)

        return inds

    def get_cat_ordinal_inds(self):

        cat_keys = self.covar_scopes['categorical']
        ordinal_keys = self.covar_scopes['ordinal categorical']

        cat_inds = [self.get_inds_from_scope(k) for k in cat_keys]
        ordinal_inds = self.get_inds_from_scope(ordinal_keys)

        return cat_inds, ordinal_inds

    def get_strat_inds(self):

        return self.get_train_inds_from_keys(self.strat_keys)