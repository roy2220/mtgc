from src import conflux


@conflux.TABLE_PIPELINE("root")
class Root:
    @conflux.FIRST_NODE()
    def step_1(self) -> conflux.Next:
        if conflux.Test("MyKey", "eq", 100):
            return conflux.Next(self.step_3)
        elif conflux.Test("MyKey", "in", [200, 300]):
            return conflux.Next(self.step_4)
        elif conflux.Test("MyKey", "eq", 100) or not (
            conflux.Test("MyKey", "in", [200, 300]) or conflux.Test("MyKey", "eq", "11")
        ):
            return conflux.Next(self.step_5)
        else:
            return conflux.Next(self.step_2)

    @conflux.NODE("yyy")
    def step_2(self) -> conflux.Next:
        return conflux.Next(self.step_3)

    @conflux.NODE("yyy")
    def step_3(self) -> conflux.Next:
        return conflux.Next(self.step_4)

    @conflux.NODE("yyy")
    def step_4(self) -> conflux.Next:
        return conflux.Next(self.step_5)

    @conflux.NODE("xxx")
    def step_5(self) -> conflux.Next:
        return conflux.Next(None)


@conflux.TABLE_MATCH_TRANSFORM("参数解析")
class RawPostback:
    @conflux.BUSINESS_UNIT("参数解析")
    def RawPostback(self) -> conflux.Set:
        return conflux.Set(
            "获取所有参数",
            [
                (
                    "RawPostback_AdjustAdMediationPlatform",
                    'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "adjust_ad_mediation_platform")',
                ),
            ],
        )
        # return [
        #     conflux.set(
        #         "adjust_ad_mediation_platform参数获取",
        #         "RawPostback_AdjustAdMediationPlatform",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "adjust_ad_mediation_platform")',
        #     ),
        #     conflux.set(
        #         "adjust_ad_revenue_network参数获取",
        #         "RawPostback_AdjustAdRevenueNetwork",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "adjust_ad_revenue_network")',
        #     ),
        #     conflux.set(
        #         "adjust_ad_revenue_placement参数获取",
        #         "RawPostback_AdjustAdRevenuePlacement",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "adjust_ad_revenue_placement")',
        #     ),
        #     conflux.set(
        #         "adjust_ad_revenue_unit参数获取",
        #         "RawPostback_AdjustAdRevenueUnit",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "adjust_ad_revenue_unit")',
        #     ),
        #     conflux.set(
        #         "adjust_id参数获取",
        #         "RawPostback_AdjustId",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "adjust_id")',
        #     ),
        #     conflux.set(
        #         "ad_network参数获取",
        #         "RawPostback_AdNetwork",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ad_network")',
        #     ),
        #     conflux.set(
        #         "ad_revenue参数获取",
        #         "RawPostback_AdRevenue",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ad_revenue")',
        #     ),
        #     conflux.set(
        #         "ad_revenue_currency参数获取",
        #         "RawPostback_AdRevenueCurrency",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ad_revenue_currency")',
        #     ),
        #     conflux.set(
        #         "ad_revenue_network参数获取",
        #         "RawPostback_AdRevenueNetwork",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ad_revenue_network")',
        #     ),
        #     conflux.set(
        #         "ad_revenue_unit参数获取",
        #         "RawPostback_AdRevenueUnit",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ad_revenue_unit")',
        #     ),
        #     conflux.set(
        #         "app_id参数获取",
        #         "RawPostback_AppId",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "app_id")',
        #     ),
        #     conflux.set(
        #         "appsflyer_id参数获取",
        #         "RawPostback_AppsflyerId",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "appsflyer_id")',
        #     ),
        #     conflux.set(
        #         "app_version参数获取",
        #         "RawPostback_AppVersion",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "app_version")',
        #     ),
        #     conflux.set(
        #         "brand参数获取",
        #         "RawPostback_Brand",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "brand")',
        #     ),
        #     conflux.set(
        #         "bundle_id参数获取",
        #         "RawPostback_BundleId",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "bundle_id")',
        #     ),
        #     conflux.set(
        #         "campuuid参数获取",
        #         "RawPostback_Campuuid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "campuuid")',
        #     ),
        #     conflux.set(
        #         "carrier参数获取",
        #         "RawPostback_Carrier",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "carrier")',
        #     ),
        #     conflux.set(
        #         "clickid参数获取",
        #         "RawPostback_Clickid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "clickid")',
        #     ),
        #     conflux.set(
        #         "combo参数获取",
        #         "RawPostback_Combo",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "combo")',
        #     ),
        #     conflux.set(
        #         "conversion_duration参数获取",
        #         "RawPostback_ConversionDuration",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "conversion_duration")',
        #     ),
        #     conflux.set(
        #         "country参数获取",
        #         "RawPostback_Country",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "country")',
        #     ),
        #     conflux.set(
        #         "currency参数获取",
        #         "RawPostback_Currency",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "currency")',
        #     ),
        #     conflux.set(
        #         "currency_type参数获取",
        #         "RawPostback_CurrencyType",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "currency_type")',
        #     ),
        #     conflux.set(
        #         "device参数获取",
        #         "RawPostback_Device",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "device")',
        #     ),
        #     conflux.set(
        #         "device_type参数获取",
        #         "RawPostback_DeviceType",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "device_type")',
        #     ),
        #     conflux.set(
        #         "devid参数获取",
        #         "RawPostback_Devid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "devid")',
        #     ),
        #     conflux.set(
        #         "event_name参数获取",
        #         "RawPostback_EventName",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "event_name")',
        #     ),
        #     conflux.set(
        #         "event_time参数获取",
        #         "RawPostback_EventTime",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "event_time")',
        #     ),
        #     conflux.set(
        #         "event_value参数获取",
        #         "RawPostback_EventValue",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "event_value")',
        #     ),
        #     conflux.set(
        #         "gaid参数获取",
        #         "RawPostback_Gaid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "gaid")',
        #     ),
        #     conflux.set(
        #         "idfa参数获取",
        #         "RawPostback_Idfa",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "idfa")',
        #     ),
        #     conflux.set(
        #         "idfv参数获取",
        #         "RawPostback_Idfv",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "idfv")',
        #     ),
        #     conflux.set(
        #         "imei参数获取",
        #         "RawPostback_Imei",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "imei")',
        #     ),
        #     conflux.set(
        #         "install_begin_time参数获取",
        #         "RawPostback_InstallBeginTime",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "install_begin_time")',
        #     ),
        #     conflux.set(
        #         "install_finish_time参数获取",
        #         "RawPostback_InstallFinishTime",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "install_finish_time")',
        #     ),
        #     conflux.set(
        #         "install_time参数获取",
        #         "RawPostback_InstallTime",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "install_time")',
        #     ),
        #     conflux.set(
        #         "ip参数获取",
        #         "RawPostback_Ip",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ip")',
        #     ),
        #     conflux.set(
        #         "language参数获取",
        #         "RawPostback_Language",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "language")',
        #     ),
        #     conflux.set(
        #         "mac参数获取",
        #         "RawPostback_Mac",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mac")',
        #     ),
        #     conflux.set(
        #         "match_type参数获取",
        #         "RawPostback_MatchType",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "match_type")',
        #     ),
        #     conflux.set(
        #         "md5_devid参数获取",
        #         "RawPostback_Md5Devid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "md5_devid")',
        #     ),
        #     conflux.set(
        #         "md5_gaid参数获取",
        #         "RawPostback_Md5Gaid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "md5_gaid")',
        #     ),
        #     conflux.set(
        #         "md5_idfa参数获取",
        #         "RawPostback_Md5Idfa",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "md5_idfa")',
        #     ),
        #     conflux.set(
        #         "md5_idfv参数获取",
        #         "RawPostback_Md5Idfv",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "md5_idfv")',
        #     ),
        #     conflux.set(
        #         "md5_imei参数获取",
        #         "RawPostback_Md5Imei",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "md5_imei")',
        #     ),
        #     conflux.set(
        #         "md5_mac参数获取",
        #         "RawPostback_Md5Mac",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "md5_mac")',
        #     ),
        #     conflux.set(
        #         "md5_oaid参数获取",
        #         "RawPostback_Md5Oaid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "md5_oaid")',
        #     ),
        #     conflux.set(
        #         "mintegral_currency参数获取",
        #         "RawPostback_MintegralCurrency",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mintegral_currency")',
        #     ),
        #     conflux.set(
        #         "mobvista_brand参数获取",
        #         "RawPostback_MobvistaBrand",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_brand")',
        #     ),
        #     conflux.set(
        #         "mobvista_campuuid参数获取",
        #         "RawPostback_MobvistaCampuuid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_campuuid")',
        #     ),
        #     conflux.set(
        #         "mobvista_clickid参数获取",
        #         "RawPostback_MobvistaClickid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_clickid")',
        #     ),
        #     conflux.set(
        #         "mobvista_combo参数获取",
        #         "RawPostback_MobvistaCombo",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_combo")',
        #     ),
        #     conflux.set(
        #         "mobvista_country参数获取",
        #         "RawPostback_MobvistaCountry",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_country")',
        #     ),
        #     conflux.set(
        #         "mobvista_device参数获取",
        #         "RawPostback_MobvistaDevice",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_device")',
        #     ),
        #     conflux.set(
        #         "mobvista_devid参数获取",
        #         "RawPostback_MobvistaDevid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_devid")',
        #     ),
        #     conflux.set(
        #         "mobvista_gaid参数获取",
        #         "RawPostback_MobvistaGaid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_gaid")',
        #     ),
        #     conflux.set(
        #         "mobvista_imei参数获取",
        #         "RawPostback_MobvistaImei",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_imei")',
        #     ),
        #     conflux.set(
        #         "mobvista_ip参数获取",
        #         "RawPostback_MobvistaIp",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_ip")',
        #     ),
        #     conflux.set(
        #         "mobvista_mac参数获取",
        #         "RawPostback_MobvistaMac",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_mac")',
        #     ),
        #     conflux.set(
        #         "mobvista_os参数获取",
        #         "RawPostback_MobvistaOs",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_os")',
        #     ),
        #     conflux.set(
        #         "mobvista_pl参数获取",
        #         "RawPostback_MobvistaPl",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_pl")',
        #     ),
        #     conflux.set(
        #         "mobvista_type参数获取",
        #         "RawPostback_MobvistaType",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "mobvista_type")',
        #     ),
        #     conflux.set(
        #         "model参数获取",
        #         "RawPostback_Model",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "model")',
        #     ),
        #     conflux.set(
        #         "monetary参数获取",
        #         "RawPostback_Monetary",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "monetary")',
        #     ),
        #     conflux.set(
        #         "oaid参数获取",
        #         "RawPostback_Oaid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "oaid")',
        #     ),
        #     conflux.set(
        #         "orig_monetary参数获取",
        #         "RawPostback_OrigMonetary",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "orig_monetary")',
        #     ),
        #     conflux.set(
        #         "os参数获取",
        #         "RawPostback_Os",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "os")',
        #     ),
        #     conflux.set(
        #         "pixel_cid参数获取",
        #         "RawPostback_PixelCid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "pixel_cid")',
        #     ),
        #     conflux.set(
        #         "pixel_oneid参数获取",
        #         "RawPostback_PixelOneid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "pixel_oneid")',
        #     ),
        #     conflux.set(
        #         "pixel_reqid参数获取",
        #         "RawPostback_PixelReqid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "pixel_reqid")',
        #     ),
        #     conflux.set(
        #         "pixel_uid参数获取",
        #         "RawPostback_PixelUid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "pixel_uid")',
        #     ),
        #     conflux.set(
        #         "pl参数获取",
        #         "RawPostback_Pl",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "pl")',
        #     ),
        #     conflux.set(
        #         "ra_adn_offer_id参数获取",
        #         "RawPostback_RaAdnOfferId",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ra_adn_offer_id")',
        #     ),
        #     conflux.set(
        #         "ra_adrev_network_name参数获取",
        #         "RawPostback_RaAdrevNetworkName",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ra_adrev_network_name")',
        #     ),
        #     conflux.set(
        #         "ra_adrev_placement参数获取",
        #         "RawPostback_RaAdrevPlacement",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ra_adrev_placement")',
        #     ),
        #     conflux.set(
        #         "ra_adrev_unit参数获取",
        #         "RawPostback_RaAdrevUnit",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ra_adrev_unit")',
        #     ),
        #     conflux.set(
        #         "ra_data_source参数获取",
        #         "RawPostback_RaDataSource",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ra_data_source")',
        #     ),
        #     conflux.set(
        #         "ra_data_source_type参数获取",
        #         "RawPostback_RaDataSourceType",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ra_data_source_type")',
        #     ),
        #     conflux.set(
        #         "ra_postback_id_info参数获取",
        #         "RawPostback_RaPostbackIdInfo",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ra_postback_id_info")',
        #     ),
        #     conflux.set(
        #         "reattribution_time参数获取",
        #         "RawPostback_ReattributionTime",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "reattribution_time")',
        #     ),
        #     conflux.set(
        #         "reject_reason参数获取",
        #         "RawPostback_RejectReason",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "reject_reason")',
        #     ),
        #     conflux.set(
        #         "sdk_version参数获取",
        #         "RawPostback_SdkVersion",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "sdk_version")',
        #     ),
        #     conflux.set(
        #         "sha1_devid参数获取",
        #         "RawPostback_Sha1Devid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "sha1_devid")',
        #     ),
        #     conflux.set(
        #         "sha1_gaid参数获取",
        #         "RawPostback_Sha1Gaid",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "sha1_gaid")',
        #     ),
        #     conflux.set(
        #         "sha1_idfa参数获取",
        #         "RawPostback_Sha1Idfa",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "sha1_idfa")',
        #     ),
        #     conflux.set(
        #         "sha1_imei参数获取",
        #         "RawPostback_Sha1Imei",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "sha1_imei")',
        #     ),
        #     conflux.set(
        #         "sub_id参数获取",
        #         "RawPostback_SubId",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "sub_id")',
        #     ),
        #     conflux.set(
        #         "type参数获取",
        #         "RawPostback_Type",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "type")',
        #     ),
        #     conflux.set(
        #         "ua参数获取",
        #         "RawPostback_Ua",
        #         'map_get(RawPostback_StubHttpRequestMessage_Payload_UrlQuery, "ua")',
        #     ),
        # ]
