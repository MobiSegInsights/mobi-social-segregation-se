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
df.deso.visi <- dbGetQuery(con, 'SELECT deso, weekday, holiday, time_seq, evenness_income AS visi
                                 FROM segregation.mobi_seg_deso')
df.deso.resi <- dbGetQuery(con, "SELECT region AS deso, evenness AS resi
                                 FROM segregation.resi_seg_deso WHERE var='income'")
df.deso <- merge(df.deso.visi, df.deso.resi, on='deso', how='left')
df.deso <- df.deso %>%
  group_by(weekday, holiday, time_seq) %>%
  summarise(Visiting=median(visi),
            Visiting_upper=quantile(visi, 0.75),
            Visiting_lower=quantile(visi, 0.25),
            Residential=median(resi),
            Residential_upper=quantile(resi, 0.75),
            Residential_lower=quantile(resi, 0.25)) %>%
  mutate(Group=interaction(as.factor(weekday), as.factor(holiday)))
df.deso$Group <- plyr::mapvalues(df.deso$Group,
          from=c('0.0', "0.1", "1.0", "1.1"),
          to=c('Non-holiday weekdays', "Non-holiday weekends",
               "Holiday weekdays", "Holiday weekends"))
g1 <- plot.time.seg(df.deso, 'Visiting income segregation')

# Visiting segregation - ICE
df.deso.visi.ice <- dbGetQuery(con, 'SELECT deso, weekday, holiday, time_seq, ice_birth AS visi
                                 FROM segregation.mobi_seg_deso')
df.deso.resi.ice <- dbGetQuery(con, "SELECT region AS deso, ice AS resi
                                 FROM segregation.resi_seg_deso WHERE var='birth_region'")
df.deso.ice <- merge(df.deso.visi.ice, df.deso.resi.ice, on='deso', how='left')
df.deso.ice <- df.deso.ice %>%
  group_by(weekday, holiday, time_seq) %>%
  summarise(Visiting=median(visi),
            Visiting_upper=quantile(visi, 0.75),
            Visiting_lower=quantile(visi, 0.25),
            Residential=median(resi),
            Residential_upper=quantile(resi, 0.75),
            Residential_lower=quantile(resi, 0.25)) %>%
  mutate(Group=interaction(as.factor(weekday), as.factor(holiday)))
df.deso.ice$Group <- plyr::mapvalues(df.deso.ice$Group,
          from=c('0.0', "0.1", "1.0", "1.1"),
          to=c('Non-holiday weekdays', "Non-holiday weekends",
               "Holiday weekdays", "Holiday weekends"))
g3 <- plot.time.seg(df.deso.ice, 'Visiting nativity segregation')

# Experienced segregation
df.indi <- dbGetQuery(con, 'SELECT region AS deso, weekday, holiday, time_seq,
                                     evenness_income AS visi, evenness_income_resi AS resi
                                     FROM segregation.mobi_seg_deso_individual')
df.indi <- df.indi %>%
  group_by(weekday, holiday, time_seq) %>%
  summarise(Visiting=median(visi, na.rm = T),
            Visiting_upper=quantile(visi, 0.75, na.rm = T),
            Visiting_lower=quantile(visi, 0.25, na.rm = T),
            Residential=median(resi, na.rm = T),
            Residential_upper=quantile(resi, 0.75, na.rm = T),
            Residential_lower=quantile(resi, 0.25, na.rm = T)) %>%
  mutate(Group=interaction(as.factor(weekday), as.factor(holiday)))
df.indi$Group <- plyr::mapvalues(df.indi$Group,
          from=c('0.0', "0.1", "1.0", "1.1"),
          to=c('Non-holiday weekdays', "Non-holiday weekends",
               "Holiday weekdays", "Holiday weekends"))
g2 <- plot.time.seg(df.indi, 'Experienced income segregation')

# Experienced segregation - ICE
df.indi.ice <- dbGetQuery(con, 'SELECT region AS deso, weekday, holiday, time_seq,
                                     evenness_income AS visi
                                     FROM segregation.mobi_seg_deso_individual')
df.indi.resi.ice <- dbGetQuery(con, "SELECT region AS deso, ice AS resi
                                 FROM segregation.resi_seg_deso WHERE var='birth_region'")
df.indi.ice <- merge(df.indi.ice, df.indi.resi.ice, on='deso', how='left')
df.indi.ice <- df.indi.ice %>%
  group_by(weekday, holiday, time_seq) %>%
  summarise(Visiting=median(visi, na.rm = T),
            Visiting_upper=quantile(visi, 0.75, na.rm = T),
            Visiting_lower=quantile(visi, 0.25, na.rm = T),
            Residential=median(resi, na.rm = T),
            Residential_upper=quantile(resi, 0.75, na.rm = T),
            Residential_lower=quantile(resi, 0.25, na.rm = T)) %>%
  mutate(Group=interaction(as.factor(weekday), as.factor(holiday)))
df.indi.ice$Group <- plyr::mapvalues(df.indi.ice$Group,
          from=c('0.0', "0.1", "1.0", "1.1"),
          to=c('Non-holiday weekdays', "Non-holiday weekends",
               "Holiday weekdays", "Holiday weekends"))
g4 <- plot.time.seg(df.indi.ice, 'Experienced nativity segregation')

G <- ggarrange(g1, g2, common.legend = TRUE, legend="bottom",
               ncol = 2, nrow = 1, labels = c('(a)', '(b)'))
ggsave(filename = paste0("figures/", 'seg_temporal.png'), plot=G,
       width = 10, height = 6, unit = "in", dpi = 300)

G2 <- ggarrange(g3, g4, common.legend = TRUE, legend="bottom",
               ncol = 2, nrow = 1, labels = c('(a)', '(b)'))
ggsave(filename = paste0("figures/", 'seg_temporal_ice.png'), plot=G2,
       width = 10, height = 6, unit = "in", dpi = 300)