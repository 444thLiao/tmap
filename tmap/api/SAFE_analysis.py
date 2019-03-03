from tmap.tda.utils import read_graph
from tmap.api.general import logger, data_parser, write_data
from tmap.netx.SAFE import SAFE_batch, get_SAFE_summary
import argparse,pickle
import pandas as pd


def preprocess_metadata(paths, filetype='csv',):
    datas = [data_parser(path, ft=filetype, verbose=0) for path in paths]
    if len(set([_.shape[0] for _ in datas])) != 1:
        logger("Accepting multiple metadata files, but with different number of row.", verbose=1)
        return
    else:
        cols_dict = {path: df.columns for path, df in zip(paths, datas)}
        data = pd.concat(datas, axis=1)
        return data, cols_dict


def generate_SAFE_score(graph, metadata, n_iter=1000, pval=0.05, nr_threshold=0.5, _mode='enrich', _cal_type='df',verbose=1):
    collect_result = {"enrich": '',
                      "decline": '',
                      "raw": {"enrich": '',
                              "decline": ''},
                      'mode': _mode}
    if _mode == 'both':
        enriched_SAFE, declined_SAFE = SAFE_batch(graph, meta_data=metadata, n_iter=n_iter,
                                                  nr_threshold=nr_threshold, _cal_type=_cal_type, _mode=_mode,verbose=verbose)
        enriched_SAFE_summary = get_SAFE_summary(graph=graph, meta_data=metadata, safe_scores=enriched_SAFE,
                                                 n_iter_value=n_iter, p_value=pval)
        declined_SAFE_summary = get_SAFE_summary(graph=graph, meta_data=metadata, safe_scores=declined_SAFE,
                                                 n_iter_value=n_iter, p_value=pval)
        collect_result['raw']['enrich'] = enriched_SAFE
        collect_result['raw']['decline'] = declined_SAFE
        collect_result['enrich'] = enriched_SAFE_summary.sort_values('SAFE enriched score',ascending=False)
        collect_result['decline'] = declined_SAFE_summary.sort_values('SAFE enriched score',ascending=False)
    else:
        SAFE_data = SAFE_batch(graph, meta_data=metadata, n_iter=n_iter,
                               nr_threshold=nr_threshold, _cal_type=_cal_type, _mode=_mode,verbose=verbose)
        SAFE_summary = get_SAFE_summary(graph=graph, meta_data=metadata, safe_scores=SAFE_data,
                                        n_iter_value=n_iter, p_value=pval)
        collect_result['raw']['enrich'] = SAFE_data
        collect_result['raw']['decline'] = SAFE_data
        collect_result['enrich'] = SAFE_summary.sort_values('SAFE enriched score',ascending=False)
        collect_result['decline'] = SAFE_summary.sort_values('SAFE enriched score',ascending=False)
    return collect_result


def main(graph, metadata, prefix, cols_dict, n_iter=1000, pval=0.05, nr_threshold=0.5, _mode='enrich', _cal_type='df',
         method='pickle',  raw=0, verbose=1):
    logger("Loding precomputed graph from", graph, verbose=1)
    graph = read_graph(graph, method=method)
    result = generate_SAFE_score(graph, metadata, n_iter=n_iter,
                                 pval=pval, nr_threshold=nr_threshold,
                                 _mode=_mode, _cal_type=_cal_type,
                                 verbose=verbose)
    if len(cols_dict) > 1:
        if _mode != 'both':
            write_data(result[_mode],prefix,suffix=_mode,mode='multidf',verbose=verbose,df2cols=cols_dict)
        else:
            write_data(result['enrich'], prefix, suffix='enrich', mode='multidf', verbose=verbose, df2cols=cols_dict)
            write_data(result['decline'], prefix, suffix='decline', mode='multidf', verbose=verbose, df2cols=cols_dict)
    else:
        if _mode != 'both':
            write_data(result[_mode], prefix, suffix=_mode, mode='df', verbose=verbose)
        else:
            write_data(result['enrich'], prefix, suffix='enrich', mode='df', verbose=verbose)
            write_data(result['decline'], prefix, suffix='decline', mode='df', verbose=verbose)

    if raw:
        if _mode != 'both':
            pickle.dump(result['raw'][_mode], open(prefix+'_raw_%s' % _mode, 'wb'))
        else:
            pickle.dump(result['raw']['enrich'], open(prefix + '_raw_%s' % 'enrich', 'wb'))
            pickle.dump(result['raw']['decline'], open(prefix + '_raw_%s' % 'decline', 'wb'))
            if len(cols_dict)>1:
                pickle.dump(cols_dict, open(prefix + '_raw_coldict', 'wb'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-G", "--graph", help="Graph file computed from 'Network_generator.py'.",
                        required=True)
    parser.add_argument("-M", "--metadata", nargs='*', help="Metadata files need to calculate the SAFE score.",
                        required=True)
    parser.add_argument("-O", "--output", help="Prefix of output, doesn't need to add suffix like .csv",
                        required=True, type=str)
    parser.add_argument("-i", "--iter", help="The number of times to shuffle for calculating SAFE. [1000]",
                        default=1000, type=int)
    parser.add_argument("-p", "--pvalue",
                        help="p-val for decide which level of data should consider as significant enriched/declined.",
                        default='0.05', type=float)
    parser.add_argument("-nt", "--nr_threshold", help="The threshold for deciding the distance from centroide to \
                                                      neighbours among pairwise distance between all nodes.",
                        type=float, default=0.5)
    parser.add_argument("--mode", help="[enrich|decline|both] Calculating mode for SAFE.",
                        type=str, default='enrich')
    parser.add_argument("-ft", "--file_type",
                        help="File type of metadata you provide [csv|xlsx]. Separtor could be tab, comma, or others.",
                        type=str, default='csv')
    parser.add_argument("--cal_type", help="Normally doesn't change. [df|dict|auto]",
                        type=str, default='df')
    parser.add_argument("--method",
                        help="Method for read graph file. [pickle] other method will be implemented at future.",
                        type=str, default='pickle')
    parser.add_argument("-r", "--raw", help="Output raw SAFE score or just SAFE summary.",
                        action="store_true")
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()
    verbose = args.verbose
    graph = args.graph
    metadata = args.metadata
    prefix = args.output
    n_iter = args.iter
    pval = args.pvalue

    metadata, cols_dict = preprocess_metadata(metadata,filetype=args.file_type)
    main(graph=graph,
         metadata=metadata,
         prefix=prefix,
         n_iter=n_iter,
         pval=pval,
         nr_threshold=args.nr_threshold,
         _mode=args.mode,
         _cal_type=args.cal_type,
         method=args.method,
         raw=args.raw,
         cols_dict=cols_dict)
