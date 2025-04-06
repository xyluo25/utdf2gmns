'''
##############################################################
# Created Date: Wednesday, March 26th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''
import pandas as pd


def cvt_lane_df_to_dict(df_lane: pd.DataFrame) -> dict:
    """Convert UTDF lane DataFrame to dictionary.
    """

    # get unique intersection id
    int_id_lst = list(df_lane['INTID'].unique())

    # convert utdf_lane dataframe to dictionary
    lane_dict = {}
    for int_id in int_id_lst:
        df_lane_int = df_lane[df_lane['INTID'] == int_id]
        df_lane_int.set_index("RECORDNAME", inplace=True)
        del df_lane_int['INTID']

        lane_dict[int_id] = df_lane_int.to_dict('dict')

        empty_key = []
        # Remove invalid turning movement
        for key in lane_dict[int_id].keys():
            if not lane_dict[int_id][key]['Up Node']:  # Up Node is empty
                empty_key.append(key)
        for key in empty_key:
            del lane_dict[int_id][key]

    return lane_dict
