# Title     : Residential, experienced, and preference-reduced experienced
# Objective : Parallel coords of nativitiy segregation
# Created by: Yuan Liao
# Created on: 2023-9-25

library(GGally)
library(ggplot2)
library(ggpubr)
library(scico)
library(dplyr)
library(arrow)
library(scales)
library(ggExtra)
library(ggthemes)
options(scipen=10000)

#------------ Three ICEs --------------
fake_scico <- scico(3, palette = "vik")
df.ice <- as.data.frame(read_parquet('results/seg_pref_reduced.parquet'))

df2plot <- sample_n(df.ice, 10000)
g <- ggparcoord(df2plot[,c('ice_r_grp', 'ice_r', 'ice_e', 'ice_ep')],
                mapping=aes(color=as.factor(ice_r_grp)), showPoints = TRUE,
                columns = c(2, 3, 4), groupColumn = 1,
                splineFactor = 5, alphaLines=0.3, scale = 'globalminmax') +
  scale_color_manual("Residents", values = c(fake_scico[3], fake_scico[2], fake_scico[1]),
                     labels=c('F', 'N', 'D')) +
  scale_x_discrete(name ="Nativity segregation",
                    limits=c("Residential","Experienced","Preference-reduced")) +
  labs(title = '(a)') +
  theme_hc()


ggsave(filename = "figures/seg_pref_reduced.png", plot=g,
       width = 4, height = 3, unit = "in", dpi = 300)