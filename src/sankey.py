import pandas as pd


def make_sankey_graph(
    df, 
    cat_cols, 
    value_col,
    size=10,
    height=1000,
    decimals=False,
    hide_label_cols=[]):

    # populate the Sankey data
    labelList = []
    nodeLabelList = []
    for catCol in cat_cols:
        labelListTemp = list(set(df[catCol].values))        
        labelList = labelList + labelListTemp
        if catCol in hide_label_cols:
            nodeLabelList = nodeLabelList + [""] * len(labelListTemp)
        else:
            nodeLabelList = nodeLabelList + labelListTemp

    # remove duplicates from labelList
    labelList = list(dict.fromkeys(labelList))

    # transform df into a source-target pair
    for i in range(len(cat_cols)-1):
        if i==0:
            sourceTargetDf = df[[cat_cols[i], cat_cols[i+1], value_col]]
            sourceTargetDf.columns = ['source','target','value']
        else:
            tempDf = df[[cat_cols[i],cat_cols[i+1],value_col]]
            tempDf.columns = ['source','target','value']
            sourceTargetDf = pd.concat([sourceTargetDf,tempDf])
        sourceTargetDf = sourceTargetDf.groupby(['source','target']).agg({'value':'sum'}).reset_index()

    # add index for source-target pair
    sourceTargetDf['sourceID'] = sourceTargetDf['source'].apply(lambda x: labelList.index(x))
    sourceTargetDf['targetID'] = sourceTargetDf['target'].apply(lambda x: labelList.index(x))

    linkLabels = []
    for c in cat_cols:
        linkLabels += [c] * df[c].nunique()

    # create the Sankey diagram
    pad = 5
    node_thickness = 20
    line_width = .25
    data = dict(
        type='sankey',
        orientation='h',
        domain=dict(x=[0,1], y=[0,1]),
        arrangement='freeform',
        node=dict(
          thickness=node_thickness,
          line=dict(width=line_width), 
          label=nodeLabelList,
          customdata=linkLabels,
          hovertemplate="<br>".join([
                "<b>%{label}</b>",
                "$%{value:,.2f}" if decimals else "$%{value:,.0f}"
                "<extra></extra>"
            ])
        ),
        link=dict(
          source=sourceTargetDf['sourceID'],
          target=sourceTargetDf['targetID'],
          value=sourceTargetDf['value'],
          hovertemplate="<br>".join([
                "<b>%{source.label} -> %{target.label}</b>",
                "$%{value:,.2f}" if decimals else "$%{value:,.0f}",
                "<extra></extra>"
            ])
        )
    )
    layout = dict(
        font=dict(size=size), 
        height=height,
        autosize=True,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    fig = dict(
        data=[data], 
        layout=layout
    )
    return fig
