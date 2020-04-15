import pandas as pd

import numpy as np
import time

from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

from .extensions.Col_Selector import ColTransformer, InPlaceColTransformer
from sklearn.preprocessing import FunctionTransformer
from collections import Counter


from sklearn.pipeline import Pipeline
from copy import deepcopy

from .Models import MODELS
from ..helpers.ML_Helpers import (conv_to_list, proc_input,
                                  get_possible_init_params,
                                  get_obj_and_params,
                                  user_passed_param_check,
                                  f_array, param_len_check,
                                  type_check, wrap_pipeline_objs,
                                  is_array_like)

from .extensions.Selector import selector_wrapper

from .Models import AVALIABLE as AVALIABLE_MODELS
from .Feature_Selectors import AVALIABLE as AVALIABLE_SELECTORS
from .Ensembles import AVALIABLE as AVALIABLE_ENSEMBLES


from .Samplers import get_sampler_and_params
from .Feature_Selectors import get_feat_selector_and_params
from .Metrics import get_metric
from .Scalers import get_scaler_and_params
from .Transformers import get_transformer_and_params, Transformer_Wrapper
from .Imputers import get_imputer_and_params
from .Loaders import get_loader_and_params, Loader_Wrapper
from .Ensembles import get_ensemble_and_params, Ensemble_Wrapper
from sklearn.ensemble import VotingClassifier, VotingRegressor
from .Feat_Importances import get_feat_importances_and_params
from .Metrics import get_metric

from .Base_Model_Pipeline import Base_Model_Pipeline

import os

from ..helpers.ML_Helpers import proc_type_dep_str

class Model_Pipeline():
    '''Helper class for handling all of the different parameters involved in
    model training, scaling, handling different datatypes ect...
    '''

    def __init__(self, pipeline_params, problem_spec, CV, Data_Scopes,
                 progress_bar, compute_train_score, _print=print):

        # Save problem spec as sp
        self.ps = problem_spec
        self.progress_bar = progress_bar
        self.compute_train_score = compute_train_score

        # Init scopes all keys, based on scope + target key
        self.all_keys = Data_Scopes.set_all_keys(spec=self.ps)
        
        # Set passed values
        self.CV = CV
        self.progress_bar = progress_bar
        self._print = _print

        # Default params
        self._set_default_params()

        # Set / proc metrics
        self.metric_strs, self.metrics, _ =\
            self._process_metrics(self.ps.metric)

        # Set / proc feat importance info
        self.feat_importances_params =  pipeline_params.feat_importances
        self.feat_importances =\
            self._process_feat_importances(self.feat_importances_params.obj)

        # Get the model specs from problem_spec
        model_spec = self.ps.get_model_spec()
        
        # Init the Base_Model_Pipeline, which creates the pipeline pieces
        self.base_model_pipeline =\
            Base_Model_Pipeline(pipeline_params=pipeline_params,
                                model_spec=model_spec,
                                Data_Scopes=Data_Scopes,
                                _print=self._print)

    def _set_default_params(self):
        
        self.n_splits_ = None

        self.flags = {'linear': False,
                      'tree': False}

    def _process_metrics(self, in_metrics):

        from .Metrics import AVALIABLE as AVALIABLE_METRICS

        # get metric_strs as initially list
        metric_strs = conv_to_list(in_metrics)

        metric_strs = proc_type_dep_str(metric_strs, AVALIABLE_METRICS, self.ps.problem_type)

        metrics = [get_metric(metric_str)
                   for metric_str in metric_strs]

        metric = metrics[0]

        return metric_strs, metrics, metric

    def _process_feat_importances(self, feat_importances):

        from .Feat_Importances import AVALIABLE as AVALIABLE_IMPORTANCES

        # Grab feat_importance from spec as a list
        feat_importances = conv_to_list(feat_importances)

        if feat_importances is not None:

            # Need to update this w/ exposed feat_importances, aka
            # not getting this values via extra params / params
            # not 100% sure what it will look like yet

            '''
            names, _ =\
                proc_type_dep_str(self.p.feat_importances, AVALIABLE_IMPORTANCES,
                                  self.extra_params, self.p.problem_type)

            params = param_len_check(names, self.p.feat_importances_params,
                                     _print=self._print)

            feat_importances =\
                [get_feat_importances_and_params(name, self.extra_params,
                                                 param, self.p.problem_type,
                                                 self.p.n_jobs)
                for name, param in zip(names, params)]

            return feat_importances
            ''' 

            return []
        return []

    def _get_subjects_overlap(self, subjects):
        '''Computer overlapping subjects with self.ps._final_subjects'''

        if self.ps._final_subjects is None:
            overlap = set(subjects)
        else:
            overlap = self.ps._final_subjects.intersection(set(subjects))

        return np.array(list(overlap))

    def Evaluate(self, data, train_subjects, splits, n_repeats, splits_vals):
        '''Method to perform a full evaluation
        on a provided model type and training subjects, according to
        class set parameters.

        Parameters
        ----------
        data : pandas DataFrame
            ABCD_ML formatted, with both training and testing data.

        train_subjects : array-like
            An array or pandas Index of the train subjects should be passed.

        Returns
        ----------
        array-like of array-like
            numpy array of numpy arrays,
            where each internal array contains the raw scores as computed for
            all passed in metrics, computed for each fold within
            each repeat.
            e.g., array will have a length of `n_repeats` * n_splits
            (num folds) and each internal array will have the same length
            as the number of metrics.
        '''

        # Set train_subjects according to self.ps._final_subjects
        train_subjects = self._get_subjects_overlap(train_subjects)

        # Init raw_preds_df
        self._init_raw_preds_df(train_subjects)

        # Setup the desired eval splits
        subject_splits =\
            self._get_eval_splits(train_subjects, splits,
                                  n_repeats, splits_vals)

        all_train_scores, all_scores = [], []
        fold_ind = 0

        if self.progress_bar is not None:
            repeats_bar = self.progress_bar(total=n_repeats,
                                            desc='Repeats')

            folds_bar = self.progress_bar(total=self.n_splits_,
                                          desc='Folds')

        self.n_test_per_fold = []

        # For each split with the repeated K-fold
        for train_subjects, test_subjects in subject_splits:

            self.n_test_per_fold.append(len(test_subjects))

            # Fold name verbosity
            repeat = str((fold_ind // self.n_splits_) + 1)
            fold = str((fold_ind % self.n_splits_) + 1)
            self._print(level='name')
            self._print('Repeat: ', repeat, '/', n_repeats, ' Fold: ',
                        fold, '/', self.n_splits_, sep='', level='name')

            if self.progress_bar is not None:
                repeats_bar.n = int(repeat) - 1
                repeats_bar.refresh()

                folds_bar.n = int(fold) - 1
                folds_bar.refresh()

            # Run actual code for this evaluate fold
            start_time = time.time()
            train_scores, scores = self.Test(data, train_subjects,
                                             test_subjects, fold_ind)

            # Time by fold verbosity
            elapsed_time = time.time() - start_time
            time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            self._print('Time Elapsed:', time_str, level='time')

            # Score by fold verbosity
            if self.compute_train_score:
                for i in range(len(self.metric_strs)):
                    self._print('train ', self.metric_strs[i], ': ',
                                train_scores[i], sep='', level='score')

            for i in range(len(self.metric_strs)):
                self._print('val ', self.metric_strs[i], ': ',
                            scores[i], sep='', level='score')

            all_train_scores.append(train_scores)
            all_scores.append(scores)
            fold_ind += 1

        if self.progress_bar is not None:
            repeats_bar.n = n_repeats
            repeats_bar.refresh()
            repeats_bar.close()

            folds_bar.n = self.n_splits_
            folds_bar.refresh()
            folds_bar.close()

        # If any local feat importances
        for feat_imp in self.feat_importances:
            feat_imp.set_final_local()

        # self.micro_scores = self._compute_micro_scores()

        # Return all scores
        return (np.array(all_train_scores), np.array(all_scores),
                self.raw_preds_df, self.feat_importances)

    def _get_eval_splits(self, train_subjects, splits, n_repeats, splits_vals):

        if splits_vals is None:

            self.n_splits_ = splits

            subject_splits =\
                self.CV.repeated_k_fold(train_subjects, n_repeats,
                                        self.n_splits_, self.ps.random_state,
                                        return_index=False)

        else:

            # Set num splits
            self.n_splits_ =\
                self.CV.get_num_groups(train_subjects, splits_vals)

            # Generate the leave-out CV
            subject_splits =\
                self.CV.repeated_leave_one_group_out(train_subjects,
                                                     n_repeats,
                                                     splits_vals,
                                                     return_index=False)

        return subject_splits

    def Test(self, data, train_subjects, test_subjects, fold_ind='test'):
        '''Method to test given input data, training a model on train_subjects
        and testing the model on test_subjects.

        Parameters
        ----------
        data : pandas DataFrame
            ABCD_ML formatted, with both training and testing data.

        train_subjects : array-like
            An array or pandas Index of train subjects should be passed.

        test_subjects : array-like
            An array or pandas Index of test subjects should be passed.

        Returns
        ----------
        array-like
            A numpy array of scores as determined by the passed
            metric/scorer(s) on the provided testing set.
        '''

        # Ensure train and test subjects are just the requested overlap
        train_subjects = self._get_subjects_overlap(train_subjects)
        test_subjects = self._get_subjects_overlap(test_subjects)

        # Ensure data being used is just the selected col / feats
        data = data[self.all_keys] 

        # Init raw_preds_df
        if fold_ind == 'test':

            if self.compute_train_score:
                self._init_raw_preds_df(np.concatenate([train_subjects,
                                                        test_subjects]))
            else:
                self._init_raw_preds_df(test_subjects)

        # Assume the train_subjects and test_subjects passed here are final.
        train_data = data.loc[train_subjects]
        test_data = data.loc[test_subjects]

        self._print('Train shape:', train_data.shape, level='size')
        self._print('Val/Test shape:', test_data.shape, level='size')

        # Wrap in search CV if needed / set to self.Model
        self.Model = self._get_final_model(train_data)

        # Train the model(s)
        self._train_model(train_data)

        # Proc the different feat importances
        self._proc_feat_importance(train_data, test_data, fold_ind)

        # Get the scores
        if self.compute_train_score:
            train_scores = self._get_scores(train_data, 'train_', fold_ind)
        else:
            train_scores = 0

        scores = self._get_scores(test_data, '', fold_ind)

        if fold_ind == 'test':

            return (train_scores, scores, self.raw_preds_df,
                    self.feat_importances)

        return train_scores, scores

    def _get_final_model(self, train_data):

        if self.base_model_pipeline.is_search():

            # get search cv, None if no search
            search_cv = self._get_search_cv(train_data.index)

            # Get search metric
            search_metric, weight_search_metric =\
                self._get_score_metric(self.base_model_pipeline.param_search.metric,
                                       self.base_model_pipeline.param_search.weight_metric)

        else:
            search_cv, search_metric = None, None
            
        # Get wrapped final model
        return self.base_model_pipeline.get_search_wrapped_pipeline(search_cv,
                                                                    search_metric,
                                                                    weight_search_metric,
                                                                    self.ps.random_state)

    def _get_search_cv(self, train_data_index):

        search_split_vals, search_splits =\
            self.base_model_pipeline.get_search_split_vals()

        if search_split_vals is None:
            search_cv = self.CV.k_fold(train_data_index, search_splits,
                                       random_state=self.ps.random_state,
                                       return_index=True)

        else:
            search_cv = self.CV.leave_one_group_out(train_data_index,
                                                    search_split_vals,
                                                    return_index=True)

        return search_cv

    def _get_score_metric(self, base_metric, weight_metric):

        # If passed metric is default, set to class defaults
        if base_metric == 'default':
            base_metric = self.ps.metric
            weight_metric = self.ps.weight_metric

        _, _, metric = self._process_metrics(base_metric)
        return metric, weight_metric

    def _get_base_fitted_pipeline(self):

        if hasattr(self.Model, 'name') and self.Model.name == 'nevergrad':
            return self.Model.best_estimator_

        return self.Model

    def _get_base_fitted_model(self):

        base_pipeline = self._get_base_fitted_pipeline()
        last_name = base_pipeline.steps[-1][0]
        base_model = base_pipeline[last_name]

        return base_model

    def _set_model_flags(self):

        base_model = self._get_base_fitted_model()

        try:
            base_model.coef_
            self.flags['linear'] = True
        except AttributeError:
            pass

        try:
            base_model.feature_importances_
            self.flags['tree'] = True
        except AttributeError:
            pass

    def _proc_feat_importance(self, train_data, test_data, fold_ind):

        # Ensure model flags are set / there are feat importances to proc
        if len(self.feat_importances) > 0:
            self._set_model_flags()
        else:
            return

        # Process each feat importance
        for feat_imp in self.feat_importances:

            split = feat_imp.split

            # Init global feature df
            if fold_ind == 0 or fold_ind == 'test':

                X, y = self._get_X_y(train_data, X_as_df=True)
                feat_imp.init_global(X, y)

            # Local init - Test
            if fold_ind == 'test':

                if split == 'test':
                    X, y = self._get_X_y(test_data, X_as_df=True)

                elif split == 'train':
                    X, y = self._get_X_y(train_data, X_as_df=True)

                elif split == 'all':
                    X, y =\
                        self._get_X_y(pd.concat([train_data, test_data]),
                                      X_as_df=True)

                feat_imp.init_local(X, y, test=True, n_splits=None)

            # Local init - Evaluate
            elif fold_ind % self.n_splits_ == 0:

                X, y = self._get_X_y(pd.concat([train_data, test_data]),
                                     X_as_df=True)

                feat_imp.init_local(X, y, n_splits=self.n_splits_)

            self._print('Calculate', feat_imp.name, 'feat importances',
                        level='name')

            # Get base fitted model
            base_model = self._get_base_fitted_model()

            # Optionally proc train, though train is always train
            if feat_imp.get_data_needed_flags(self.flags):
                X_train = self._proc_X_train(train_data)
            else:
                X_train = None

            # Test depends on scope
            if split == 'test':
                test = test_data
            elif split == 'train':
                test = train_data
            elif split == 'all':
                test = pd.concat([train_data, test_data])

            # Always proc test.
            X_test, y_test = self._proc_X_test(test)

            try:
                fold = fold_ind % self.n_splits_
            except TypeError:
                fold = 'test'

            # Process the feature importance, provide all needed
            feat_imp.proc_importances(base_model, X_test, y_test=y_test,
                                      X_train=X_train, scorer=self.metric,
                                      fold=fold,
                                      random_state=self.ps.random_state)

            # For local, need an intermediate average, move df to dfs
            if isinstance(fold_ind, int):
                if fold_ind % self.n_splits_ == self.n_splits_-1:
                    feat_imp.proc_local()

    def _get_X_y(self, data, X_as_df=False, copy=False):
        '''Helper method to get X,y data from ABCD ML formatted df.

        Parameters
        ----------
        data : pandas DataFrame
            ABCD ML formatted.

        X_as_df : bool, optional
            If True, return X as a pd DataFrame,
            otherwise, return as a numpy array

            (default = False)

        copy : bool, optional
            If True, return a copy of X

            (default = False)

        Returns
        ----------
        array-like
            X data for ML
        array-like
            y target for ML
        '''

        if copy:
            X = data.drop(self.ps.target, axis=1).copy()
            y = data[self.ps.target].copy()
        else:
            X = data.drop(self.ps.target, axis=1)
            y = data[self.ps.target]

        if not X_as_df:
            X = np.array(X).astype(float)

        y = np.array(y).astype(float)

        return X, y

    def _train_model(self, train_data):
        '''Helper method to train a models given
        a str indicator and training data.

        Parameters
        ----------
        train_data : pandas DataFrame
            ABCD_ML formatted, training data.

        Returns
        ----------
        sklearn api compatible model object
            The trained model.
        '''

        # Data, score split
        X, y = self._get_X_y(train_data)

        # Fit the model
        self.Model.fit(X, y)

        # If a search object, show the best params
        self._show_best_params()

    def _show_best_params(self):

        try:
            name = self.Model.name
        except AttributeError:
            return

        all_params, names = self.base_model_pipeline.get_all_params_with_names()
        self._print('Params Selected by Best Pipeline:', level='params')

        for params, name in zip(all_params, names):

            if len(params) > 0:

                to_show = []
                all_ps = self.Model.best_estimator_.get_params()

                for p in params:

                    ud = params[p]

                    if type_check(ud):
                        to_show.append(p + ': ' + str(all_ps[p]))

                if len(to_show) > 0:
                    self._print(name, level='params')

                    for show in to_show:
                        self._print(show, level='params')

                    self._print('', level='params')

    def _get_scores(self, test_data, eval_type, fold_ind):
        '''Helper method to get the scores of
        the trained model saved in the class on input test data.
        For all metrics/scorers.

        Parameters
        ----------
        test_data : pandas DataFrame
            ABCD ML formatted test data.

        eval_type : {'train_', ''}

        fold_ind : int or 'test'

        Returns
        ----------
        float
            The score of the trained model on the given test data.
        '''

        # Data, score split
        X_test, y_test = self._get_X_y(test_data)

        # Add raw preds to raw_preds_df
        self._add_raw_preds(X_test, y_test, test_data.index, eval_type,
                            fold_ind)

        # Get the scores
        scores = [metric(self.Model, X_test, y_test)
                  for metric in self.metrics]

        return np.array(scores)

    def _add_raw_preds(self, X_test, y_test, subjects, eval_type, fold_ind):

        if fold_ind == 'test':
            fold = 'test'
            repeat = ''
        else:
            fold = str((fold_ind % self.n_splits_) + 1)
            repeat = str((fold_ind // self.n_splits_) + 1)

        self.classes = np.unique(y_test)

        # Catch case where there is only one class present in y_test
        # Assume in this case that it should be binary, 0 and 1
        if len(self.classes) == 1:
            self.classes = np.array([0, 1])

        try:
            raw_prob_preds = self.Model.predict_proba(X_test)
            pred_col = eval_type + repeat + '_prob'

            if len(np.shape(raw_prob_preds)) == 3:

                for i in range(len(raw_prob_preds)):
                    p_col = pred_col + '_class_' + str(self.classes[i])
                    class_preds = [val[1] for val in raw_prob_preds[i]]
                    self.raw_preds_df.loc[subjects, p_col] = class_preds

            elif len(np.shape(raw_prob_preds)) == 2:

                for i in range(np.shape(raw_prob_preds)[1]):
                    p_col = pred_col + '_class_' + str(self.classes[i])
                    class_preds = raw_prob_preds[:, i]
                    self.raw_preds_df.loc[subjects, p_col] = class_preds

            else:
                self.raw_preds_df.loc[subjects, pred_col] = raw_prob_preds

        except AttributeError:
            pass

        raw_preds = self.Model.predict(X_test)
        pred_col = eval_type + repeat

        if len(np.shape(raw_preds)) == 2:
            for i in range(np.shape(raw_preds)[1]):
                p_col = pred_col + '_class_' + str(self.classes[i])
                class_preds = raw_preds[:, i]
                self.raw_preds_df.loc[subjects, p_col] = class_preds

        else:
            self.raw_preds_df.loc[subjects, pred_col] = raw_preds

        self.raw_preds_df.loc[subjects, pred_col + '_fold'] = fold

        # Make copy of true values
        if len(np.shape(y_test)) > 1:
            for i in range(len(self.ps.target)):
                self.raw_preds_df.loc[subjects, self.ps.target[i]] =\
                    y_test[:, i]

        elif isinstance(self.ps.target, list):
            t_base_key = '_'.join(self.ps.target[0].split('_')[:-1])
            self.raw_preds_df.loc[subjects, 'multiclass_' + t_base_key] =\
                y_test

        else:
            self.raw_preds_df.loc[subjects, self.ps.target] = y_test

    def _init_raw_preds_df(self, subjects):

        self.raw_preds_df = pd.DataFrame(index=subjects)

    def _proc_X_test(self, test_data):
        
        # Grab the test data, X as df + copy
        X_test, y_test = self._get_X_y(test_data, X_as_df=True, copy=True)

        #Get the base pipeline
        pipeline = self._get_base_fitted_pipeline()

        return pipeline.proc_X_test(X_test, y_test)

    def _proc_X_train(self, train_data):

        # Get X,y train
        X_train, y_train = self._get_X_y(train_data, copy=True)

        #Get the base pipeline
        pipeline = self._get_base_fitted_pipeline()

        return pipeline.proc_X_train(X_train, y_train)