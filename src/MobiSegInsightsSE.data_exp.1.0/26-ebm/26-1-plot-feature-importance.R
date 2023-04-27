# Title     : Importance of features
# Objective : Visualize the importance of features
# Created by: Yuan Liao
# Created on: 2023-04-24

library(dplyr)
library(ggplot2)

# ---------- Model on all individuals ------
df <- read.csv('./results/ebm/all/f_score.csv')
colors <- df$Color[order(df$Score, decreasing = TRUE)]
df <- df %>% arrange(Score)
df$Name <- factor(df$Name,
                 levels=df$Name,
                 labels=df$Name)
g <- ggplot(data=df, aes(y=Name, x=Score)) +
  theme_minimal() +
  labs(y='Feature',
       x='Importance score') +
  geom_point(size=3) +
  xlim(0, 0.015) +
  geom_segment(aes(y=Name,
                   yend=Name,
                   x=min(Score),
                   xend=max(Score)),
               linetype="dashed",
               linewidth=0.3) +
  theme(legend.position = "none",
        panel.grid = element_blank(),
        panel.background = element_blank(),
        text = element_text(size=15),
        plot.caption = element_text(hjust = 0, face= "italic"),
        axis.text.y = element_text(colour = df$Color[as.integer(df$Name)]))
ggsave(filename = "figures/ebm_features.png", plot=g,
       width = 10, height = 10, unit = "in", dpi = 300)


# ---------- Model on all individuals ------
df <- read.csv('./results/ebm/feature_importance.csv')
df <- df %>% arrange(Low.income, decreasing=TRUE)
df$Name <- factor(df$Name,
                 levels=df$Name,
                 labels=df$Name)
g1 <- ggplot(data = df, aes(x=Name)) +
  geom_segment(aes(xend=Name, y=High.income, yend=Low.income), color="grey") +
  geom_point(aes(y=High.income, color='High income'), size=3 ) +
  geom_point(aes(y=Low.income, color='Low income'), size=3 ) +
  scale_color_manual(name='Income group', breaks=c('Low income', 'High income'),
                     values=c('High income'='steelblue', 'Low income'='orange')) +
  coord_flip() +
  theme_minimal() +
  theme(legend.position = "top",
        panel.grid = element_blank(),
        panel.background = element_blank(),
        text = element_text(size=15),
        axis.text.y = element_text(colour = df$Color[as.integer(df$Name)])) +
  xlab("Feature name") +
  ylab("Score")

ggsave(filename = "figures/ebm_features_top10.png", plot=g1,
       width = 8, height = 7, unit = "in", dpi = 300)