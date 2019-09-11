from ABCD_ML.ML_Helpers import get_objects_by_type, get_objects
from ABCD_ML.Metrics import get_metrics_by_type

from ABCD_ML.Models import AVALIABLE as AVALIABLE_MODELS
from ABCD_ML.Models import MODELS

from ABCD_ML.Imputers import IMPUTERS
from ABCD_ML.Scalers import SCALERS

from ABCD_ML.Samplers import AVALIABLE as AVALIABLE_SAMPLERS
from ABCD_ML.Samplers import SAMPLERS

from ABCD_ML.Feature_Selectors import AVALIABLE as AVALIABLE_SELECTORS
from ABCD_ML.Feature_Selectors import SELECTORS

from ABCD_ML.Ensembles import AVALIABLE as AVALIABLE_ENSEMBLES
from ABCD_ML.Ensembles import ENSEMBLES

from ABCD_ML.Default_Params import PARAMS


def get_name(obj):

    name = obj.__module__ + '.' + obj.__qualname__

    name = name.replace('.tree.tree', '.tree')
    name = name.replace('.tree.tree', '.tree')

    base_replace_list = ['logistic', 'gpc', 'gpr', 'classification',
                         'regression', 'coordinate_descent', 'sklearn',
                         'forest', 'classes', 'base', 'multilayer_perceptron',
                         'univariate_selection', 'minimum_difference', 'deskl',
                         'exponential', 'logarithmic', 'rrc', 'data',
                         'variance_threshold']

    for r in base_replace_list:
        name = name.replace('.' + r + '.', '.')

    splits = name.split('.')
    for split in splits:
        if split.startswith('_'):
            name = name.replace('.' + split + '.', '.')

    return name


def get_metric_name(obj):

    name = obj.__name__
    name = name.replace('_wrapper', '')
    name = 'sklearn.metrics.' + name

    return name


def main_category(lines, name):

    lines.append('.. _' + name + ':')
    lines.append(' ')

    stars = ''.join('*' for i in range(len(name)))
    lines.append(stars)
    lines.append(name)
    lines.append(stars)

    lines.append('')

    return lines


def add_block(lines, problem_types, AVALIABLE=None, OBJS=None):
    '''If AVALIABLE and OBJS stay none, assume that showing metrics'''

    for pt in problem_types:
        lines.append(pt)
        lines.append(''.join('=' for i in range(len(pt))))

        if AVALIABLE is None and OBJS is None:
            objs = get_metrics_by_type(pt)
            metric = True

        else:
            objs = get_objects_by_type(pt, AVALIABLE, OBJS)
            metric = False

        for obj in objs:
            lines = add_obj(lines, obj, metric=metric)

        lines.append('')

    return lines


def add_no_type_block(lines, OBJS):

    lines.append('All Problem Types')
    lines.append('=================')

    objs = get_objects(OBJS)

    for obj in objs:
        lines = add_obj(lines, obj, metric=False)

    lines.append('')
    return lines


def add_obj(lines, obj, metric=False):
    '''Obj as (obj_str, obj, obj_params),
    or if metric = True, can have just
    obj_str and obj.'''

    obj_str = '"' + obj[0] + '"'
    lines.append(obj_str)
    lines.append(''.join(['*' for i in range(len(obj_str))]))
    lines.append('')

    if metric:
        o_path = get_metric_name(obj[1])
        lines.append('  Base Func Documenation: :func:`' + o_path + '`')
    else:
        o_path = get_name(obj[1])
        lines.append('  Base Class Documenation: :class:`' + o_path + '`')
        lines = add_params(lines, obj[2])

    lines.append('')
    return lines


def add_params(lines, obj_params):

    lines.append('')
    lines.append('  Param Distributions')
    lines.append('')

    for p in range(len(obj_params)):

        # Get name
        params_name = obj_params[p]
        lines.append('\t' + str(p) + '. "' + params_name + '" ::')
        lines.append('')

        # Show info on the params
        params = PARAMS[params_name].copy()
        if len(params) > 0:
            lines = add_param(lines, params)
        else:
            lines.append('\t\tdefaults only')

        lines.append('')

    return lines


def add_param(lines, params):

    for key in params:

        line = '\t\t' + key + ': '
        value = params[key]

        if 'scipy' in str(type(value)):

            if isinstance(value.a, int):
                line += 'Random Integer Distribution ('
                line += str(value.a) + ', ' + str(value.b) + ')'

            else:
                a, b = value.interval(1)

                # Rought heuristic...
                if a == 0:
                    line += 'Random Uniform Distribution ('
                elif b/a < 11:
                    line += 'Random Uniform Distribution ('
                else:
                    line += 'Random Reciprical Distribution ('

                line += str(a) + ', ' + str(b) + ')'

        elif len(value) == 1:
            if callable(value[0]):
                line += str(value[0].__name__)
            else:
                line += str(value[0])

        elif len(value) > 50:
            line += 'Too many params to show'

        else:
            line += str(value)

        lines.append(line)
    return lines


problem_types = ['binary', 'regression', 'categorical multilabel',
                 'categorical multiclass']

lines = []

lines = main_category(lines, 'Model Types')

lines.append('Different availible choices for the `model_type` parameter' +
             ' are shown below.')
lines.append('`model_type` is accepted by ' +
             ':func:`Evaluate <ABCD_ML.ABCD_ML.ABCD_ML.Evaluate>` and ' +
             ':func:`Test <ABCD_ML.ABCD_ML.ABCD_ML.Test>`.')
lines.append('The exact str indicator for each `model_type` is represented' +
             ' by the sub-heading (within "")')
lines.append('The avaliable models are further broken down by which can work' +
             'with different problem_types.')
lines.append('Additionally, a link to the original models documentation ' +
             'as well as the implemented parameter distributions are shown.')
lines.append('')

lines = add_block(lines, problem_types, AVALIABLE_MODELS, MODELS)

lines = main_category(lines, 'Metrics')

lines.append('Different availible choices for the `metric` parameter' +
             ' are shown below.')
lines.append('`metric` is accepted by ' +
             ':func:`Evaluate <ABCD_ML.ABCD_ML.ABCD_ML.Evaluate>` and ' +
             ':func:`Test <ABCD_ML.ABCD_ML.ABCD_ML.Test>`.')
lines.append('The exact str indicator for each `metric` is represented by' +
             'the sub-heading (within "")')
lines.append('The avaliable metrics are further broken down by which can' +
             ' work with different problem_types.')
lines.append('Additionally, a link to the original models documentation ' +
             'is shown.')
lines.append('Note: When supplying the metric as a str indicator you do' +
             'not need to include the prepended "multiclass"')
lines.append('')

lines = add_block(lines, problem_types)

lines = main_category(lines, 'Imputers')
lines.append('Different availible choices for the `imputer` parameter' +
             ' are shown below.')
lines.append('imputer is accepted by ' +
             ':func:`Evaluate <ABCD_ML.ABCD_ML.ABCD_ML.Evaluate>` and ' +
             ':func:`Test <ABCD_ML.ABCD_ML.ABCD_ML.Test>`.')
lines.append('The exact str indicator for each `imputer` is represented' +
             ' by the sub-heading (within "")')
lines.append('Additionally, a link to the original imputers documentation ' +
             'as well as the implemented parameter distributions are shown.')
lines.append('Imputers are also special, in that a model_type can be passed ' +
             'instead of the imputer str. In that case, the model_type will' +
             ' be used to fill any NaN by column.')
lines.append('For `imputer_scope` of float, or custom column names, only ' +
             'regression type models are valid, and for scope of categorical' +
             ', only binary / multiclass model types are valid!')
lines.append('The sklearn iterative imputer is used when a model_type is' +
             ' passed.')
lines.append('Also, if a model_type is passed, then the `imputer_params`' +
             ' argument will then be considered as applied to the base ' +
             ' estimator / model_type!')
lines.append('')
lines = add_no_type_block(lines, IMPUTERS)

lines = main_category(lines, 'Scalers')
lines.append('Different availible choices for the `scaler` parameter' +
             ' are shown below.')
lines.append('scaler is accepted by ' +
             ':func:`Evaluate <ABCD_ML.ABCD_ML.ABCD_ML.Evaluate>` and ' +
             ':func:`Test <ABCD_ML.ABCD_ML.ABCD_ML.Test>`.')
lines.append('The exact str indicator for each `scaler` is represented' +
             ' by the sub-heading (within "")')
lines.append('Additionally, a link to the original scalers documentation ' +
             'as well as the implemented parameter distributions are shown.')
lines.append('')
lines = add_no_type_block(lines, SCALERS)

lines = main_category(lines, 'Samplers')
lines.append('Different availible choices for the `sampler` parameter' +
             ' are shown below.')
lines.append('`sampler` is accepted by ' +
             ':func:`Evaluate <ABCD_ML.ABCD_ML.ABCD_ML.Evaluate>` and ' +
             ':func:`Test <ABCD_ML.ABCD_ML.ABCD_ML.Test>`.')
lines.append('The exact str indicator for each `sampler` is represented' +
             ' by the sub-heading (within "")')
lines.append('The avaliable samplers are further broken down by which ' +
             ' work with with different problem_types.')
lines.append('Additionally, a link to the original samplers documentation ' +
             'as well as the implemented parameter distributions are shown.')
lines.append('')
lines = add_block(lines, problem_types, AVALIABLE_SAMPLERS, SAMPLERS)

lines = main_category(lines, 'Feat Selectors')
lines.append('Different availible choices for the `feat_selector` parameter' +
             ' are shown below.')
lines.append('`feat_selector` is accepted by ' +
             ':func:`Evaluate <ABCD_ML.ABCD_ML.ABCD_ML.Evaluate>` and ' +
             ':func:`Test <ABCD_ML.ABCD_ML.ABCD_ML.Test>`.')
lines.append('The exact str indicator for each `feat_selector` is' +
             ' represented by the sub-heading (within "")')
lines.append('The avaliable feat selectors are further broken down by which ' +
             'can work with different problem_types.')
lines.append('Additionally, a link to the original feat selectors ' +
             ' documentation ' +
             'as well as the implemented parameter distributions are shown.')
lines.append('')
lines = add_block(lines, problem_types, AVALIABLE_SELECTORS, SELECTORS)

lines = main_category(lines, 'Ensemble Types')
lines.append('Different availible choices for the `ensemble_type` parameter' +
             ' are shown below.')
lines.append('`ensemble_type` is accepted by ' +
             ':func:`Evaluate <ABCD_ML.ABCD_ML.ABCD_ML.Evaluate>` and ' +
             ':func:`Test <ABCD_ML.ABCD_ML.ABCD_ML.Test>`.')
lines.append('The exact str indicator for each `ensemble_type` is' +
             ' represented by the sub-heading (within "")')
lines.append('The avaliable ensemble types are further broken down by which ' +
             'can work with different problem_types.')
lines.append('Additionally, a link to the original ensemble types ' +
             ' documentation ' +
             'as well as the implemented parameter distributions are shown.')
lines.append('')
lines = add_block(lines, problem_types, AVALIABLE_ENSEMBLES, ENSEMBLES)


with open('options.rst', 'w') as f:
    for line in lines:
        f.write(line)
        f.write('\n')