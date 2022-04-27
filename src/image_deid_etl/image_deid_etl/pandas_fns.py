
def merge_left_only(df1,df2,df1_on=[],df2_on=[]):
    if df1_on:
        df3 = df1.merge(df2,left_on=df1_on,right_on=df2_on,how='left',indicator=True)
        df3 = df3[df3['_merge']=='left_only'].drop(columns=[df2_on,'_merge'])
    else:
        df3 = df1.merge(df2,how='left',indicator=True)
        df3 = df3[df3['_merge']=='left_only'].drop(columns=['_merge'])
    return df3