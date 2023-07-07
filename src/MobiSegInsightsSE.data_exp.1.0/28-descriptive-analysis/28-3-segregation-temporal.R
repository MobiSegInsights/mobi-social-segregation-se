# Title     : Income segregation dynamics
# Objective : Visiting/Experienced vs. resi.
# Created by: Yuan Liao
# Created on: 2023-05-08

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(yaml)
library(DBI)
library(DescTools)
options(scipen=10000)

keys_manager <- read_yaml('./dbs/keys.yaml')
user <- keys_manager$database$user
password <- keys_manager$database$password
port <- keys_manager$database$port
db_name <- keys_manager$database$name
con <- DBI::dbConnect(RPostgres::Postgres(),
                      host = "localhost",
                      dbname = db_name,
                      user = user,
                      password = password,
                      port = port)
# Define plotting function
plot.time.seg <- function(df, y.lb){
  g <- ggplot(data=df) +
  geom_line(aes(x=time_seq/2, y=Visiting_upper, color=Group), alpha=0.3, linetype = "dashed") +
  geom_line(aes(x=time_seq/2, y=Visiting_lower, color=Group), alpha=0.3, linetype = "dashed") +
  geom_line(aes(x=time_seq/2, y=Visiting, color=Group)) +
  geom_line(aes(x=time_seq/2, y=Residential), color='gray45') +
  labs(x='Hour of day (h)', y=y.lb) +
  theme_minimal()
  return(g)
}

# Visiting segregation
df.deso <- as.data.frame(read_parquet('results/data4model.parquet'))
df.deso <- df.deso %>%
  group_by(weekday, holiday, time_seq) %>%
  summarise(Visiting=median(ice_birth),
            Visiting_upper=quantile(ice_birth, 0.75),
            Visiting_lower=quantile(ice_birth, 0.25),
            Residential=median(ice_birth_resi),
            Residential_upper=quantile(ice_birth_resi, 0.75),
            Residential_lower=quantile(ice_birth_resi, 0.25)) %>%
  mutate(Group=interaction(as.factor(weekday), as.factor(holiday)))
df.deso$Group <- plyr::mapvalues(df.deso$Group,
          from=c('0.0', "0.1", "1.0", "1.1"),
          to=c('Non-holiday weekdays', "Non-holiday weekends",
               "Holiday weekdays", "Holiday weekends"))
g1 <- plot.time.seg(df.deso, 'Visiting nativity segregation')

# Experienced segregation
df.indi <- dbGetQuery(con, 'SELECT uid, weekday, holiday, time_seq, ice_birth, ice_birth_resi, wt_p
                                     FROM segregation.mobi_seg_deso_individual')
df.indi <- df.indi %>%
  group_by(weekday, holiday, time_seq) %>%
  summarise(Visiting=Quantile(ice_birth, wt_p, 0.5, na.rm = T),
            Visiting_upper=Quantile(ice_birth, wt_p, 0.75, na.rm = T),
            Visiting_lower=Quantile(ice_birth, wt_p, 0.25, na.rm = T),
            Residential=Quantile(ice_birth_resi, wt_p, 0.5, na.rm = T),
            Residential_upper=Quantile(ice_birth_resi, wt_p, 0.75, na.rm = T),
            Residential_lower=Quantile(ice_birth_resi, wt_p, 0.25, na.rm = T)) %>%
  mutate(Group=interaction(as.factor(weekday), as.factor(holiday)))
df.indi$Group <- plyr::mapvalues(df.indi$Group,
          from=c('0.0', "0.1", "1.0", "1.1"),
          to=c('Non-holiday weekdays', "Non-holiday weekends",
               "Holiday weekdays", "Holiday weekends"))
g2 <- plot.time.seg(df.indi, 'Experienced nativity segregation')

G <- ggarrange(g1, g2, common.legend = TRUE, legend="bottom",
               ncol = 2, nrow = 1, labels = c('(a)', '(b)'))
ggsave(filename = paste0("figures/", 'seg_temporal_ice.png'), plot=G,
       width = 10, height = 6, unit = "in", dpi = 300)